# Zachary AI × Z-Brand-Core Domain Adapter Contract

Date: 2026-09-01
Status: D1 Planned / research branch only

## Purpose

Zachary AI is the cross-product learning/core layer. Z-Brand-Core remains the authoritative Brand Intelligence domain runtime.

This contract allows Z-Brand-Core to contribute reusable, evidence-backed capability candidates without leaking product-specific schema, business rules, UI, permissions, or private data into a global core.

## Three-repository ownership

| Repository | Owner role | Must not absorb |
|---|---|---|
| Z-Brand-Core | Brand/content/event/risk domain runtime | DCC governance implementation; SICI business logic; global AI core implementation |
| SICI-Core | Product/domain runtime and mobile workflow | Z-Brand internals; DCC privileged runtime |
| Development-Command-Console | Governance, audit, tests, release gates, cross-repo contracts | Product business/UI logic; production runtime |

## Zachary capability classes

### CORE-GENERAL

Only evidence-backed, cross-domain capabilities may become global candidates: Context Understanding, Retrieval, Reasoning, Planning, Evaluation, Conflict Resolution, Repair, Tool Orchestration.

### DOMAIN-BOUND

Z-Brand-specific subject rules, CTH semantics, brand/event taxonomies, database schema, UI and collection policy remain inside Z-Brand-Core.

### ADAPTER

The bridge between Zachary AI and Z-Brand-Core. It exposes only the minimum context, tools, permissions and output contract required for an authorized task.

## Intelligence flow

```text
Platform Adapter / Collector
        ↓
Evidence + Normalization
        ↓
Subject / Content Intelligence
        ↓
Context Intelligence
        ↓
Behavior Signals
        ↓
Event Candidate
        ↓
Existing EventGraph (authoritative)
        ↓
Risk / Impact / Evidence
        ↓
Domain Result
        ↓
Experience / Pattern Candidate
        ↓
Cross-domain verification
        ↓
Zachary CORE candidate (never automatic promotion)
```

## Context firewall

Every Zachary-assisted task must carry: `product_id`, `domain_id`, `task_id`, `session_scope`, authorized data sources, authorized tools and effective rule/baseline version.

If domain, permission, provenance or temporal validity is unclear: fail closed. Do not borrow context from another product.

## Collection and model boundary

The collector remains platform-specific and must obey the existing RedNote/XHS safety gate. Context Intelligence is platform-neutral. OCR/VLM/LLM providers are replaceable adapters and cannot override deterministic subject or evidence rules.

## Promotion rule

A Context/Behavior/Event pattern is only a `promotion_candidate` after deterministic tests, evidence review, cross-domain validation and the existing DCC promotion gates. A model score alone is never sufficient.

## Production protection

This contract does not authorize changes to `SUBJECT_WORDS`, `SUBJECT_EXCLUDE_WORDS`, `subject_hit()`, `_subject_sql_and_values()`, `aggregate_events()`, `build_daily_report()`, timestamp semantics, historical data, collector authentication/risk gates, or production EventGraph semantics.

## Implementation stage

Current branch is research-only. No production runtime wiring, no automatic global-memory writes, no DCC/SICI dependency, and no automatic cross-repository promotion are introduced by this contract.
