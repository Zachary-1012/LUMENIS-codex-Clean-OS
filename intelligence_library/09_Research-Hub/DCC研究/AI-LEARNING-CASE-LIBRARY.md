# AI Learning Case Library — Unified Platform Knowledge

Status: ACTIVE / advisory / reviewable
Owner: Development-Command-Console (DCC)
Scope: Z-Brand-Core + SICI-Core + Development-Command-Console
Purpose: 将持续审计、研发、采集、数据分析、AI 舆情与三仓库协同过程中形成的可复用知识沉淀为案例；用于后续检索、回归、Shadow Learning、Regression Memory 和 Learning Promotion。

> Hard rule: Learning is advisory, never authoritative. AI-assisted conclusions are not observed facts without Evidence. No case in this library may directly modify production code, permissions, release state, subject rules, risk facts, or database truth.

## 0. Learning lifecycle

```text
Research / Repository Observation / Failure / User Feedback
        ↓
Case Capture
        ↓
Fact vs Interpretation separation
        ↓
Evidence binding
        ↓
Lesson / Pattern extraction
        ↓
Shadow evaluation
        ↓
Regression validation
        ↓
Promotion decision
        ↓
Only then: Contract / Code / Rule / Release change
```

Case states:
- OBSERVED: directly observed in repository/runtime/evidence.
- SYNTHESIZED: cross-repository synthesis based on observed facts.
- ADAPTED: external research adapted to this platform.
- SHADOW: proposed pattern not yet promoted.
- VERIFIED: independently tested with Evidence.
- PROMOTED: accepted through Change Plan + Evidence + Gate.

## 1. Architecture & ownership cases

### CASE-001 — Three-repository ownership boundary
State: SYNTHESIZED

- Z-Brand-Core: production/domain truth.
- Development-Command-Console: engineering control, verification, permission, Evidence and release gate.
- SICI-Core: mobile interaction, device and user-workflow surface.
- Shared capability must have one clear Owner.
- Other repositories consume through Contract/Evidence rather than copying internal implementation.

Lesson: Architecture stability comes from explicit ownership, not from putting all code in one repository.

### CASE-002 — DCC must not become production runtime
State: SYNTHESIZED

DCC may inspect, plan, verify and gate changes, but must not silently become a runtime dependency of Z-Brand-Core production flows.

Lesson: Engineering control plane and production execution plane must remain separable.

### CASE-003 — SICI is a surface, not a second Core
State: SYNTHESIZED

SICI can expose mobile development, GitHub interaction, testing and workflow feedback, but must not recreate business intelligence, risk truth or engineering control logic already owned elsewhere.

Lesson: A UI/control surface should consume contracts instead of cloning domain logic.

### CASE-004 — Shared capability requires a single Owner
State: SYNTHESIZED

When two repositories appear to need the same capability, first identify the canonical Owner and define the consumer Contract. Do not create a second registry/core merely because integration is inconvenient.

Lesson: Duplicate ownership creates drift, conflicting state and future migration cost.

## 2. Contract / version / runtime / Evidence cases

### CASE-005 — Contract before code
State: SYNTHESIZED

Before a cross-repository change, establish: Owner, input/output contract, dependency, runtime, Evidence requirement, test responsibility and rollback responsibility.

Lesson: Contract-first prevents a local optimization from becoming a cross-repository conflict.

### CASE-006 — Version truth hierarchy
State: REPO_OBSERVED + SYNTHESIZED

Current source/runtime facts outrank narrative documentation and historical commit titles. A VERSION file, when present and authoritative, must be treated as a version source; README labels and auto-save commit titles cannot silently override it.

Lesson: Version number is a fact source and must be reconciled before release decisions.

### CASE-007 — Evidence state cannot be collapsed
State: SYNTHESIZED

```text
PLANNED != IMPLEMENTED
IMPLEMENTED != TESTED
TESTED != VERIFIED
VERIFIED != ACCEPTED
ACCEPTED != RELEASED
```

Lesson: Every promotion step needs its own evidence boundary.

### CASE-008 — Runtime truth must match UI claims
State: REPO_OBSERVED + SYNTHESIZED

SICI currently supports browser-side JavaScript/Python/HTML execution paths while shell and native git clone/pull are constrained. UI controls must not imply capabilities that the actual runtime cannot perform.

Lesson: Capability labels are part of system correctness, not cosmetic copy.

### CASE-009 — Fixed SHA for verification dependencies
State: ADAPTED

Use fixed repository/commit references for security-sensitive reusable verification dependencies where appropriate. Keep DCC reusable workflows small and deterministic rather than creating one giant universal workflow.

Lesson: Reusability must not trade away provenance or deterministic verification.

## 3. Social-platform collection cases

### CASE-010 — Discovery is not evidence
State: SYNTHESIZED

Search/discovery results identify candidates; final analysis should prefer note/detail evidence with normalized content, author, publication time, interaction metrics and available comments/media metadata.

Lesson: Candidate discovery and evidentiary collection are separate stages.

### CASE-011 — Platform adapter boundary
State: SYNTHESIZED

Each social platform may require platform-specific authentication, browser behavior, parsing and anti-abuse handling. Those details belong in an adapter boundary; normalized records should enter a shared data contract after collection.

Lesson: Multi-platform support should add adapters, not duplicate the entire intelligence Core.

### CASE-012 — XHS authentication is not platform health
State: SYNTHESIZED

Valid cookies/session state do not prove platform health. Authentication, network reachability, platform blocking/security verification, collector state and circuit state must remain distinguishable.

Lesson: Auth success and collection health are separate signals.

### CASE-013 — Empty result is not automatically zero
State: SYNTHESIZED

A zero-result collection can mean genuine no-new-data, failed authentication, platform blocking, network failure, parser failure or an unhealthy collector. The runtime must preserve the failure state instead of reporting a misleading successful zero.

Lesson: Absence of data is a data-quality state, not a universal success result.

### CASE-014 — Circuit breaker protects the platform boundary
State: SYNTHESIZED

Repeated platform failures/security challenges should move the collector toward controlled stop/cooldown rather than unlimited retries. Recovery requires a real health check before normal collection resumes.

Lesson: Retry logic without a circuit state can amplify platform risk.

### CASE-015 — Shadow before production adapter promotion
State: SYNTHESIZED

A new collector/adapter version should first run in Shadow against controlled samples or non-authoritative flows. Compare output quality, duplication, subject precision, error states and evidence completeness before production promotion.

Lesson: New collection code must earn production authority through evidence.

## 4. Subject / data quality / time cases

### CASE-016 — Subject boundary is a business invariant
State: REPO_OBSERVED + SYNTHESIZED

For Guangzhou Taikoo Hui monitoring, the hard subject boundary must remain consistent through discovery, storage, aggregation and reporting. The protected chain includes SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit(), _subject_sql_and_values(), aggregate_events() filtering and build_daily_report() subject filters.

Lesson: Subject scope is not a convenience filter; it defines the truth domain of the product.

### CASE-017 — Never weaken subject filtering to increase recall
State: SYNTHESIZED

Adding more unrelated records may improve apparent recall while corrupting event counts, sentiment, risk, reports and brand conclusions. Precision at the subject boundary is more important than raw collection volume for a scoped monitoring product.

Lesson: Do not trade business truth for collection volume.

### CASE-018 — publish_datetime and captured_at are different facts
State: SYNTHESIZED

`publish_datetime` describes when source content was published; `captured_at` describes when the system observed/collected it. They must not be substituted for one another in trend, daily-report or event-lifecycle calculations.

Lesson: Event time and observation time are separate dimensions.

### CASE-019 — Normalize before analysis
State: SYNTHESIZED

Raw platform fields should be normalized before deduplication, classification, sentiment/risk analysis, event aggregation and reporting. Platform-specific naming should not leak into the shared intelligence contract unnecessarily.

Lesson: Normalization is the bridge between heterogeneous collectors and unified analytics.

## 5. Event / analytics / AI cases

### CASE-020 — A note is not an event
State: SYNTHESIZED

A single social note is an evidence item. An event is a higher-level aggregation around a common fact/topic/time/relationship. Event lifecycle should consider first appearance, latest appearance, volume, interaction, growth, risk and relationships.

Lesson: Event intelligence requires aggregation, not simple counting.

### CASE-021 — Four-layer intelligence model
State: SYNTHESIZED

```text
WHO             → who is communicating
WHAT            → what is being said
WHAT HAPPENED   → what event is forming
SO WHAT         → why it matters to the brand
```

Lesson: AI reporting becomes useful when it explains business meaning instead of only summarizing text.

### CASE-022 — Deterministic system remains the fact source
State: SYNTHESIZED

Rules, database records, collection evidence, event aggregation, risk calculations and statistical definitions remain authoritative. AI may explain, classify, cluster, summarize and suggest relationships, but cannot silently redefine core facts.

Lesson: AI augments the intelligence system; it does not replace the system of record.

### CASE-023 — AI failure must not stop core intelligence
State: SYNTHESIZED

AI unavailable, unconfigured or degraded must not prevent collection, subject filtering, deduplication, event processing, risk scoring, statistics or basic reporting where deterministic implementations exist.

Lesson: AI is an optional intelligence layer, not a single point of failure.

### CASE-024 — AI output provenance
State: SYNTHESIZED

AI-generated statements must carry an AI-assisted classification and remain separate from observed facts until independently supported by Evidence.

Lesson: Provenance must survive the entire learning pipeline.

### CASE-025 — Local-first AI reduces operational dependency
State: SYNTHESIZED

Prefer local/controlled AI where practical. External AI can remain optional for additional reasoning capacity. Core operation must remain functional when external providers are unavailable.

Lesson: AI provider flexibility protects availability, cost control and data boundaries.

## 6. Learning / engineering feedback cases

### CASE-026 — Failure cases are more valuable than success-only memory
State: REPO_OBSERVED + SYNTHESIZED

Learning Store explicitly separates Case, Failure Database, Pattern and Lesson. Failure classes include remote HEAD change, push rejection, merge conflict, test failure, security block, credential detection, permission drift, unexpected file change, baseline drift, deployment failure, rollback and not-verified states.

Lesson: A learning system that stores only successful outcomes will repeatedly rediscover the same failures.

### CASE-027 — Regression Memory before modification
State: SYNTHESIZED

Before a change, query known similar cases and failure patterns by repository, baseline, target files, operation type and failure reason. Use the result as a risk signal, not as an automatic veto unless a hard Gate says so.

Lesson: Past failure patterns should influence planning before code changes begin.

### CASE-028 — Learning promotion is gated
State: REPO_OBSERVED + SYNTHESIZED

The learning lifecycle is:
`Research → relevance test → adaptation → implementation → test → evidence → promotion`.

Shadow candidates remain review-required until independently validated. Workflows must not auto-promote learning into production code, permissions, release state or hard rules.

Lesson: Learning must be reviewable and reversible.

### CASE-029 — Evidence compression improves AI efficiency
State: ADAPTED + SYNTHESIZED

Stable diagnostics, failure fingerprints, evidence summaries and reusable inspection findings can reduce repeated full-context inspection. Future AI runs should consume compact verified Evidence where possible instead of repeatedly reconstructing the entire platform state.

Lesson: Good memory is both a quality mechanism and a compute/token efficiency mechanism.

## 7. Security / provenance cases

### CASE-030 — Never learn secrets
State: SYNTHESIZED

Learning records must never persist tokens, cookies, credentials, passwords or other sensitive authentication material. AI provider configuration may describe capability/state but must not store secrets.

Lesson: Learning infrastructure must have stricter data minimization than ordinary logs.

### CASE-031 — Repository provenance before external code reuse
State: ADAPTED

External research can influence architecture without copying code. Before reusing external code, verify license/provenance and record the source/adaptation boundary.

Lesson: Knowledge transfer and code copying are different operations.

### CASE-032 — Artifact provenance belongs at release, not every inspection
State: ADAPTED

Signed artifact attestations are useful for actual distributable release artifacts, but should not be treated as mandatory overhead for every routine inspection. Release provenance should connect artifact, repository, workflow, environment and commit when a release artifact exists.

Lesson: Evidence depth should match the risk and lifecycle stage.

## 8. Product / workflow cases

### CASE-033 — Mobile development is a real workflow, not a smaller desktop
State: SYNTHESIZED

SICI must account for touch interaction, viewport constraints, local storage, browser runtime limits, deployment feedback and mobile recovery paths. Desktop assumptions must not silently become mobile requirements.

Lesson: Device constraints belong in the contract and test model.

### CASE-034 — Continuous engineering is controlled iteration
State: SYNTHESIZED

The platform should continuously observe → learn → plan → change → test → evidence → release → learn again, but each transition remains gated. Continuous does not mean uncontrolled.

Lesson: The goal is a closed learning loop, not autonomous uncontrolled mutation.

## 9. Current priority learning backlog

P0 — must be converted into verified Evidence first:
1. Three-repository current SHA/version/runtime fact synchronization.
2. CTH-POMS collection → Auth → Health → Circuit → Subject → Time → Risk → Event → Report call-chain verification.
3. Subject regression protection.
4. Version truth reconciliation.
5. Evidence completeness for actual cross-repository E2E.

P1 — next promotion candidates:
1. XHS Topic evidence chain.
2. Auth/Health/Recovery state convergence.
3. SICI runtime capability truth.
4. Cross-repository Contract validation.
5. Failure fingerprints and Regression Memory integration.
6. AI-assisted analysis Shadow evaluation.

P2 — later:
1. Persistent Learning Store contract.
2. Semantic/vector similarity retrieval.
3. Automated Experience Extractor.
4. Controlled learning promotion workflow.
5. Release artifact provenance.

## 10. Promotion rule

No case becomes a hard engineering rule merely because it appears in this library.

Promotion requires:

```text
Case
→ Evidence
→ Independent validation
→ Change Plan
→ Owner approval
→ Test
→ Release Gate
→ Promotion record
```

This library is the platform's reusable memory. The repositories remain the source of truth for actual implementation and runtime state.
