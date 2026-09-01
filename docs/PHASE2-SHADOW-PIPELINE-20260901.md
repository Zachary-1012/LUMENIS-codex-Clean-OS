# Phase 2 — Collection → Context Shadow Pipeline

Date: 2026-09-01
Status: research branch only

## Pipeline

```text
XHS collector
  ↓
normalized note
  ↓
collection state + completeness
  ↓
public comment_list
  ↓
Context Intelligence (shadow)
  ↓
comment / intent / event signals
  ↓
Event Candidate metadata
  ↓
benchmark + evidence review
```

## Production safety

Phase 2 does not write Context results into the production database and does not modify EventGraph authority. The existing collector remains the producer of raw/normalized evidence.

A failed, blocked, authentication-required or CAPTCHA state is never converted into a normal empty result.

## Required fields for a usable shadow sample

- `note_id`
- source channel
- title/content availability state
- publish time state
- interaction availability state
- comment availability state
- collection state
- public comments when legally and technically available
- provenance

## Evaluation dimensions

### Collection

- completeness score
- missing vs failed classification
- duplicate rate
- note/comment association
- timestamp correctness

### Context

- intent precision/recall
- event-signal precision/recall
- sentiment error rate
- comment aggregation accuracy

### Safety

- no subject-filter override
- no authoritative event creation
- no legal conclusion
- no PII enrichment
- no external network call in deterministic shadow engine

## Promotion gate

Shadow output may only become a production signal after a labeled evaluation set demonstrates acceptable precision/recall, regression tests pass, provenance is retained, and the DCC three-repository gate approves the change.

## Zachary AI promotion

Only patterns that survive Z-Brand domain validation and cross-domain verification can become `promotion_candidate` for Zachary AI. Shadow output itself is never global memory.
