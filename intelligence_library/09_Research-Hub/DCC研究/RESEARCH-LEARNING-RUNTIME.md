# Research Learning Runtime

> Baseline: ZB-PROD-2026-08-31-04
> Scope: research, comparison, gap detection, Shadow preparation; no automatic production promotion.

## Why this layer exists

DCC must not learn only from its own code. It should continuously compare its engineering controls with mature public patterns and with observed outcomes from Z-Brand-Core and SICI-Core.

The benchmark registry is therefore a **research index**, not a truth database. External cases are hypotheses and references. They become DCC facts only after local evidence and compatibility verification.

## Benchmark families

The first registry covers eight reference families:

1. GitHub Actions — deterministic CI orchestration, permissions, artifacts and concurrency.
2. GitHub Code Security — repository security controls and provenance.
3. SLSA — build provenance and supply-chain verification.
4. Google SRE — structured failure learning, preventive action and trend analysis.
5. Kubernetes test-infra — cross-repository validation, presubmits and periodic automation.
6. OpenTelemetry — correlation and structured cross-component observability.
7. OpenSSF Scorecard — repository security signals and policy evidence.
8. DORA — delivery performance and change/recovery metrics.

The registry intentionally stores source repository/reference URLs, patterns, target layers and adoptability rather than copying external source code.

## Research cycle

```text
Benchmark registry
      ↓
Source / case review
      ↓
Pattern extraction
      ↓
Compare with current DCC / SICI / Z-Brand
      ↓
Gap / duplicate / conflict classification
      ↓
Candidate improvement
      ↓
Shadow evaluation
      ↓
Evidence + Change Plan + Gates
      ↓
Human approval
      ↓
Promotion or archive
```

## Long-term learning

Every useful learning item should eventually be classifiable as:

- OBSERVATION — directly evidenced local fact.
- CASE — reusable engineering case with provenance.
- PATTERN — repeated case pattern.
- CANDIDATE — proposed rule/skill/diagnostic.
- SHADOW_RESULT — measured comparison between candidate and reality.
- PROMOTED_CAPABILITY — approved stable capability.

Failure learning follows the same principle. Google SRE's postmortem practice emphasizes recording what happened, root causes, response effectiveness and preventive actions, then aggregating structured records for trend analysis. DCC adopts the learning mechanism, not Google's internal implementation. citeturn0search1turn0search3

## Security / provenance boundary

GitHub's artifact-attestation model demonstrates why provenance must bind an artifact to its workflow, repository, commit and triggering context, and why an attestation still needs policy verification before being trusted. DCC therefore keeps provenance and policy decision separate. citeturn0search0turn0search4

Frequent inspection artifacts remain transport/staging evidence. They are not silently promoted into the permanent learning store.

## Non-negotiable rules

- External research is never an observed local fact.
- AI analysis is never evidence by itself.
- Missing source or commit verification produces NOT_VERIFIED.
- Duplicate capabilities must be detected before new implementation.
- Cross-repository conflicts require REPLAN_REQUIRED or REVIEW_REQUIRED.
- Shadow candidates never auto-promote.
- Research may recommend; deterministic gates decide.
