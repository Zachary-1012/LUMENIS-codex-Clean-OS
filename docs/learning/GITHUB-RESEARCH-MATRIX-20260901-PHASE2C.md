# GitHub Research Matrix — Phase 2C

Date: 2026-09-01
Scope: research only; no third-party source code is copied or vendored.

## Research rule

Every engineering iteration must inspect relevant open-source cases before implementation. We extract architecture patterns, failure modes, evaluation methods, data structures, and governance ideas. We do not transplant implementation, selectors, signatures, anti-bot bypasses, credentials, or proprietary business logic.

## Cases reviewed

### MediaCrawler / XHS ecosystem
Focus: platform adapter separation, note/comment collection concerns, persistence boundaries, platform-specific failure modes.
Decision: learn adapter isolation and failure classification; reject direct source reuse and any platform-security bypass behavior.

### Crawlee Python
Focus: request queue, retry lifecycle, concurrency/autoscaling, pause/resume, storage separation.
Decision: learn stateful scheduling and backpressure concepts; implement our own CollectorGuard/Scheduler contracts.

### Scrapling
Focus: resilient parsing and selector recovery concepts.
Decision: learn parser resilience as an experiment; do not import selectors or implementation code. Recovery must remain bounded and observable.

### Label Studio
Focus: human annotation, model pre-annotation, evaluation/active-learning workflow.
Decision: adopt the concept of Ground Truth and prediction-vs-label evaluation; no dependency required for the first benchmark.

### OpenAI Evals
Focus: evaluation as versioned test cases and reproducible model comparisons.
Decision: adopt benchmark-as-code principles for our own evaluation harness; no code copied.

### RednoteAI public repositories
Focus: multimodal/OCR/VLM model capability direction.
Decision: evaluate models as replaceable adapters; no model output becomes authoritative evidence without validation.

## Z-Brand decisions

1. Collector remains the authoritative producer of raw/normalized evidence.
2. Collection quality is measured separately from intelligence quality.
3. Missing, empty, not-applicable, blocked and failed are distinct states.
4. Context/Event output remains shadow until benchmark gates pass.
5. Subject hard filters remain authoritative and cannot be overridden by models.
6. EventGraph is not mutated by shadow inference.
7. Platform adapters may evolve independently from core intelligence.
8. Third-party projects are research references, not dependencies by default.
9. Any future dependency requires license review, provenance entry and explicit architecture approval.
10. Only cross-domain validated patterns may become Zachary AI promotion candidates.

## Benchmark dimensions

Collection: coverage, fidelity, freshness, duplicate rate, association accuracy, failure classification.

Context: intent precision/recall/F1, sentiment error, topic accuracy, comment aggregation accuracy.

Event: event candidate precision/recall, event boundary accuracy, evidence traceability, false-positive rate.

Multimodal: OCR character/field accuracy, image-text alignment, extraction confidence, abstention quality.

Reliability: recovery rate, retry budget adherence, checkpoint correctness, regression rate.

Governance: provenance completeness, PII minimization, authority-boundary compliance, license/provenance audit.

## Promotion formula

Research finding -> internal experiment -> labeled benchmark -> regression pass -> domain validation -> cross-domain validation -> DCC gate -> Zachary capability candidate.

A GitHub project being popular, mature, or accurate is never sufficient evidence for promotion.
