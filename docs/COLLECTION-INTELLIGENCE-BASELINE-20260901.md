# Z-Brand Collection Intelligence Baseline

Date: 2026-09-01
Status: D1 Planned / research branch

## Objective

Build an owned, platform-neutral collection layer that maximizes useful public-data completeness and factual accuracy while remaining resilient, rate-limited, auditable and compliant.

## Core rule

Completeness does not mean unlimited collection. The target is maximum necessary information density with minimum unnecessary personal-data collection.

## Collection object

```text
Discovery → Detail → Comments → Media/OCR → Normalization → Dedup → Quality → Evidence
```

A collector failure, authentication failure, risk-control pause or incomplete page must never be represented as a legitimate zero-data result.

## Completeness dimensions

Each record receives a derived completeness score across applicable fields:

- source identity
- title/content
- publish time
- public interaction metrics
- public comments
- media availability
- OCR/visual extraction status
- author public metadata
- event context
- provenance/evidence

Missing fields must be distinguishable from not-applicable and collection-failed.

## Accuracy evaluation

Maintain a fixed human-reviewed evaluation set per platform. Every adapter change is measured against:

- field accuracy
- comment-to-note association accuracy
- duplicate rate
- timestamp accuracy
- missing-field rate
- event-signal precision/recall
- failure classification accuracy

A new collector version cannot replace the production adapter solely because it collects more records.

## Adapter contract

Each platform adapter owns only platform-specific behavior:

```text
Discovery
Detail
Comment retrieval
Media metadata
Session/auth state
Rate policy
Failure taxonomy
```

The following remain shared Core capabilities:

```text
Normalizer
Dedup
Quality
Evidence
Context
Behavior
Event
Risk
Governance
```

## Resilience

Use graceful degradation, cooldown, bounded retries, checkpoint/resume, health signals and adapter isolation. Do not bypass platform security controls, authentication challenges, CAPTCHAs or access restrictions.

When a platform changes structure:

```text
Adapter health failure
  ↓
Stop unsafe writes
  ↓
Preserve evidence/state
  ↓
Mark unavailable
  ↓
Update adapter
  ↓
Evaluation set
  ↓
Controlled promotion
```

## Multimodal path

```text
Note
 ├─ text
 ├─ image/media metadata
 └─ public comments
       ↓
OCR / VLM (replaceable adapter)
       ↓
Context Intelligence
       ↓
Event Candidate
```

OCR/VLM output is derived evidence and never silently overwrites raw source facts.

## Cross-platform roadmap

First-class deep research target: Xiaohongshu/RedNote.

Subsequent adapters are selected by evidence and public-data availability rather than by copying another platform's private implementation. All adapters must satisfy the same Core contract.

## Ownership

The collection adapter and its platform-specific implementation are owned by Z-Brand-Core. Generic extraction, evaluation, evidence and learning patterns may become Zachary AI capability candidates only after domain isolation and cross-domain verification.

## Governance

The design follows the current requirement that automated collection must not illegally intrude into or interfere with network services, and that unnecessary personal information encountered through automated collection should be deleted or anonymized as required by applicable rules. See the official Network Data Security Regulation and Personal Information Protection Compliance Audit Measures.
