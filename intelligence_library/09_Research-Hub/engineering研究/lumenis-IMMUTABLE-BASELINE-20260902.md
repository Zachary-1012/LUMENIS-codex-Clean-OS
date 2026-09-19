# Zachary AI / ZBC Immutable Baseline — 2026-09-02

## Identity
1. Zachary AI is an independent, complete AI product and may ultimately become independently commercialized/productized.
2. Before independent launch, ZBC is Zachary AI's first cultivation environment, first real-use environment, and first business training environment.
3. Zachary operates within ZBC but is not owned by or structurally defined by ZBC.
4. ZBC remains an independent product/domain boundary.

## Bidirectional learning
1. ZBC cultivates Zachary through approved ZBC data, cases, evidence, system knowledge and real-use results.
2. Zachary may return useful validated research, capabilities, reasoning improvements, product/UX improvements and engineering improvements to ZBC.
3. Return flow must be Evidence → Evaluation → Contract → Governance → Promotion.
4. Zachary general learning remains broader than ZBC; ZBC domain learning remains restricted to ZBC-related knowledge, evidence, data and cases.

## Control-plane invariants
1. DCC is the engineering control plane, not a production business runtime.
2. Evidence must distinguish expectedState from observedState.
3. NOT_VERIFIED must never be promoted to PASS without new evidence.
4. Remote HEAD changes during a material operation require stop/replan.
5. Governance authorizes; execution performs.
6. One shared capability has one authoritative Owner; consumers use Contract/Adapter boundaries.

## Functional invariants
1. Zachary remains complete; consolidation must not create a lightweight edition.
2. Mobile-first is the current delivery direction.
3. Baseline is authoritative; Supplements are additive, scoped, versioned and lifecycle-controlled.
4. Historical evidence and migration lineage remain auditable.

## Security invariants
1. No credentials, tokens, passwords or secrets in source-controlled documentation or frontend code.
2. Least privilege is the default.
3. AI output cannot bypass validation, Evidence, permission or approval gates.
4. Cross-repository changes must be bounded, reversible and auditable.

## Change rule
Identity, ownership, security, evidence and governance invariants cannot be changed by ordinary feature work. Any change requires explicit baseline-change evidence, impact analysis, migration/rollback planning and human approval.
