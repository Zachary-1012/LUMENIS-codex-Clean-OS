# Three-Repository Intelligence Convergence

Date: 2026-09-01

## Current facts

- Z-Brand-Core main: `47c73ab3a51c9507e32a2af8860717d0587066ba`
- SICI-Core main: `8be0106d7084a1402f61ad0dd4de8867c91b9db7`
- Development-Command-Console main: `684e3c7f47a9aa025b4b9f15b99d9fa6f714d68d`

All three repositories have a same-day integration-log synchronization commit, so this collection/intelligence work must be evaluated against the current three-repository baseline rather than an older Z-Brand-only baseline.

## Architecture

```text
                    Zachary AI
                 Global Core / Learning
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
      Z-Brand-Core    SICI-Core        Future Domains
       Domain AI      Domain AI          Domain AI
          │              │
          └────── Experience / Evidence ────┘
                         │
                         ↓
                        DCC
                Governance / Audit / Gate
```

## Z-Brand contribution

Z-Brand-Core supplies domain-bound experience around:

- public social-content collection
- content/context understanding
- comment-derived signals
- event discovery and relation inference
- brand intelligence
- evidence-backed risk interpretation
- multimodal note understanding

It does **not** export its business rules, production schema, UI, permissions or private data into Zachary Global Core.

## Promotion path

```text
Z-Brand observation
 → Evidence
 → Domain pattern
 → deterministic benchmark
 → cross-domain test
 → promotion candidate
 → DCC gate
 → Zachary Core candidate
```

`promotion_candidate` is not promotion.

## DCC integration

DCC remains the owner of the cross-repository change gates, evidence requirements, learning/promotion controls and security boundaries. Z-Brand-Core must not reproduce DCC's governance implementation.

The three-repository pre-change checklist is the mandatory gate for material changes touching this work.

## SICI integration

SICI remains a separate domain runtime. Shared learning must cross the adapter/evidence boundary; no direct production dependency or privileged access is introduced.

## Immediate implementation

This research branch contains:

1. `context_intelligence.py` — deterministic, platform-neutral, shadow-only context engine.
2. `tests/test_context_intelligence.py` — safety and signal tests.
3. `docs/ZACHARY-AI-DOMAIN-ADAPTER-CONTRACT-20260901.md` — ownership and context firewall contract.
4. `docs/COLLECTION-INTELLIGENCE-BASELINE-20260901.md` — collection completeness/accuracy/adapter baseline.

No production collector, subject filter, EventGraph authority or DCC/SICI runtime dependency is changed by this branch.
