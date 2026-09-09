# LUMENIS Open-Source Runtime & Research Integration V1

Status: `GOVERNANCE / SHADOW_READY TARGET`

Purpose: integrate open-source models and three research accelerators in a way that is usable after launch, isolated from Production Truth, license-traceable, resource-bounded, and replaceable by LUMENIS-native implementations later.

## Mandatory architecture

```text
Business Capability
→ LUMENIS Contract
→ LUMENIS Intelligence Router
→ Provider/Execution Adapter
→ Open-Source Runtime / Zhipu / Ollama / Codex/OpenCode
→ Health / Budget / Fallback / Evidence
```

Production Truth remains independent. External runtimes must never become required for startup, canonical data, core reporting, security, or release acceptance.

## Open-source model directory policy

Use one dedicated repository area only. Prefer an existing equivalent if present; otherwise use:

`external_open_source/`

with machine-readable registries, adapters, runtime manifests, licenses/notices, health, benchmarks, shadow experiments, evidence, tests, and research-only assets.

Large model binaries MUST NOT be committed to Git. Store manifests, hashes, source/download instructions, runtime configuration, and license metadata only.

Every model/component must be one of:
`RESEARCH_ONLY | SHADOW | PRODUCTION_CANDIDATE | PRODUCTION_APPROVED | DEPRECATED | BLOCKED`.

## AI routing policy

Use the cheapest verified layer that can safely complete the task:

`Deterministic Rule/Existing Evidence → Ollama → Zhipu → Codex/Sol → Sol High → Sol Extra High`

OpenCode is an execution/orchestration layer, not a separate truth authority.

Rules:
- no duplicate inference when valid Evidence already exists;
- Ollama handles low-risk local/repetitive tasks when capable;
- Zhipu handles ordinary analysis/preprocessing where adequate;
- Codex/Sol handles repository understanding and code execution;
- High is reserved for hard engineering/architecture/failure attribution;
- Extra High only for P0 or unresolved global conflicts;
- all autonomous research loops must have hard iteration/time/token/resource limits.

## Three research accelerators

1. Research Optimizer — reference `karpathy/autoresearch`; bounded isolated experiments and keep/reject decisions.
2. Performance Race — reference `karpathy/nanochat` speedrun methodology; same acceptance quality, lower wall-clock time.
3. Execution Efficiency Lab — reference `ScalingIntelligence/KernelBench`; adapt benchmark philosophy to current CPU/RAM/disk/SQLite/browser/worker workloads; GPU-specific work is NOT_REQUIRED until hardware/workload requires it.

These are R&D accelerators, not Production Truth. They may create candidate patches and Evidence, but may not auto-merge, auto-deploy, or mutate Production DB.

## Interaction-model research seed

Track real-time interaction-model architecture as a research seed only until an actually usable runtime/API and licensing path is verified. Architecture target: fast interaction layer + deeper background intelligence + shared context + independent Production Truth. Do not claim external model runtime integration until source/API/license/runtime evidence exists.

## Health/Fallback contract

A provider/model is ACTIVE only after a real call chain succeeds. Health states:
`UP | DEGRADED | DOWN | NOT_CONFIGURED | UNKNOWN`.

Fallback must be observable and evidence-backed. A preferred chain may be Open-Source/Ollama → Zhipu → approved cloud engineering runtime → deterministic/no-AI mode, but actual order must follow current repository policy.

## Production promotion gate

No external model or accelerator may become `PRODUCTION_APPROVED` until all are verified:
- upstream source/version/commit;
- repository license;
- model-weight license if applicable;
- relevant dataset/asset/dependency licenses;
- commercial/runtime usage compatibility;
- adapter isolation;
- health;
- fallback;
- security;
- resource budget;
- unit/integration/independence/critical E2E tests;
- Evidence;
- rollback/disable path.

## Temporary-to-native lifecycle

`External Reference → Adapter → Shadow Benchmark → Evidence → Production Candidate → LUMENIS Native Parity → Replace → Remove Dependency → Regression Proof`.

Principle: `Integrate now for release efficiency; preserve replacement freedom after launch.`
