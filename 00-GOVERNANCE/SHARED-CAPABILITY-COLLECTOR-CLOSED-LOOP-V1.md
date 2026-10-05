# SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1

> Status: APPROVED / CANONICAL INCREMENTAL EXECUTION INPUT
> Date: 2026-09-13
> Scope: `Zachary-1012/LUMENIS-codex-Clean-OS`
> Product: 序境 / LUMENIS
> Branch target: `main`

## 1. Canonical Positioning

This document defines the approved incremental architecture and execution line for integrating online collection into Shared Capability without creating a fifth product domain or a second production truth.

The immutable product chains remain:

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

and:

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

Collector is a SYSTEM-owned Runtime capability. Shared Capability consumes Collector outputs through canonical Source / Evidence contracts. CTH, BMP and Shared Capability may request collection jobs, but Collector has one Production Owner.

## 2. Unified Acquisition Contract

Manual upload, file import, API ingestion and online collection are acquisition adapters, not separate truth systems.

Target conceptual contract:

```text
SourceArtifact
- id
- origin_type: UPLOAD | COLLECTOR | IMPORT | API | MANUAL
- provider
- platform
- external_id
- source_url
- file_ref
- subject_id
- domain
- media_type
- captured_at
- published_at
- content_hash
- raw_snapshot_ref
- collector_run_id
- upload_batch_id
- access_status
- policy_status
- license_status
- provenance
- truth_state
- created_at
- updated_at
```

These names are target semantics only. Before implementation, Codex must Dependency Trace existing tables, services, routes and registries and reuse or adapt the current canonical owner. Creating a second Source / Evidence truth is forbidden.

## 3. Collector Runtime

Collector must become an adapter registry under SYSTEM Runtime:

```text
collector.xiaohongshu
collector.bilibili
collector.douyin
collector.weibo
collector.podcast
collector.web
collector.youtube
...
```

Each adapter may implement only acquisition responsibilities:

```text
discover
fetch
parse
snapshot
normalize-minimum
health
checkpoint
```

Collector output must flow through canonical Source / Evidence / Provenance. Collector must not emit business conclusions directly.

Two task types share one Runtime:

1. Discovery Collection — discovers new public content by subject, topic, account, keyword, URL and time scope.
2. Tracking Collection — revisits known content units and appends performance snapshots over time.

Tracking horizons may include T0 / T+1h / T+24h / T+3d / T+7d / T+30d, but future windows must remain scheduled or pending until real time has elapsed.

### 3.1 Current prelaunch collection and query contract — 2026-10-03

The Product Owner requires collection and new brand/commercial-entity admission
to continue alongside the other product work. Current main social-platform work
covers XHS/RedNote, Douyin, WeChat, Instagram, X and Facebook. Retain other planned
platform capability obligations; these six are not a reason to delete them.
Use genuine native publication time from 2026-01-01 through each actual capture.
Keep unknown publication time separately for review; capture time is never a
replacement publication date, and future observations cannot be invented.

The Global contract remains the single owner of country categories and the
China-first quality adjustment: finish existing country candidates and continue
excellent, regional, specialist and niche entities operating in China with global
references. Do not resurrect the superseded equal-country50+50 expansion quota.
Registry counts and four representative jobs are not full collection coverage.

Use the existing SYSTEM acquisition_plan owner. Current name/alias enumeration
alone does not implement the complete business query. Bind each derived query
to an actual entity ID/aliases, selected country/market/city or venue boundary,
business purpose, chosen topic/event dimensions and known account/URL provenance.
Keep canonical identity/scope separate from the search string; do not turn an
arbitrary string or name hit into permission or verified entity binding.

Purpose-specific paths include identity/official-account discovery, current
market/news/product/collaboration/campaign activity, consumer experience/service
feedback, creator/content/propagation work, and venue tenant/category/events.
Select relevant dimensions from the task instead of multiplying every alias by
every topic. Known authorized accounts and content URLs can enter Tracking;
unresolved identity stays Discovery/UNASSIGNED until real evidence binds it.
Guangzhou venue monitoring covers its actual in-venue tenants/activities; other
locations or a tenant brand's global campaign do not automatically belong there.
Company, brand, store and commercial venue identities/relations stay distinct.

Retain the original available body/media representation, platform/native ID,
author/account, source URL, publication/capture/observation time and precision,
native interaction metrics/units, topic/tag/mention/location/language and useful
public comment/reply/creator metadata where genuinely available. Preserve
platform-specific fields and honest NULL/UNKNOWN/UNAVAILABLE. Source-derived
sentiment/risk/relevance/event interpretation stays distinguishable from raw
facts and carries its method/version and evidence.

Admission checks exact entity/market and task relevance, locatable source content,
source identity and time quality. Navigation, login/challenge pages, fetch errors
and unrelated same-name entities are not a successful body. Classify advertising
and finance by business purpose: an advertising case may be useful, but unrelated
financial/navigation material cannot stand in for a creative brief. Preserve
original/republished lineage, use stable platform/native identity, append genuine
metric changes and retain content revisions; do not erase low-quality raw input
or turn duplicates into additional coverage. Sampled posts do not establish
representative consumer demand or causal business effects.

Platform readiness is not one boolean. Preserve separate facts for declared
capability, configuration, exact session/permission verification, worker
reachability, last real run, current run and formal Source/Evidence/Canonical
admission. A readable cookie file or configured proxy cannot produce `ACTIVE`,
`VERIFIED` or product-facing `READY`; a check timestamp must describe an actual
check, and cached verification must be judged against its freshness contract.
Do not enable a platform flag to conceal a missing authorization or callable
method. Resolve aliases through the existing canonical platform-naming owner,
while retaining historical source-platform values and their read compatibility.

The removed aggregate Collector quota is not reintroduced as a32/64-query world
limit. A bounded per-batch limit may protect runtime/account health, but remaining
queries/entities require an explicit continuation through the existing task,
checkpoint and scheduler. The business-plan checkpoint (`input_fingerprint` plus
completed query keys) is query-level continuation; it is not a platform-native
page cursor. Carry the existing checkpoint through the authorized API/task resume
path and separately persist each platform's native pagination cursor when its
adapter exposes one. A task that only calls search does not satisfy a promised
detail, comment/reply, creator/author-post or media continuation. Preserve partial
results, distinguish query-plan continuation from native pagination, and resume
without repeating accepted effects or losing failed pages. Truncation is not
completion. Keep bounded retries, polite pacing and recovery. No second Collector,
query store or scheduler.

The canonical CTH collection API and any retained V4 compatibility entry are
callers of this one Collector/Task/Permission/Source/Evidence/Canonical owner,
not separate acquisition systems. Preserve legacy task identifiers, polling,
risk handling and platform-specific behavior until each unique behavior has an
equivalent path through the canonical contract and its acceptance evidence;
then retire only the duplicated route. Never keep two independent status or
write authorities to avoid migrating a caller.

MANUAL remains the default. Only explicitly approved public prelaunch-baseline
sources or user-opted-in scopes may enter AUTO; login does not grant source use.
Use current Source/session/Permission/caller bindings and the Source→Evidence→
Canonical chain. The protected personal Mainland XHS identity and legacy9222
recovery route remain forbidden. One unavailable identity/source blocks that
path only; other approved collection and entity admission continue. Technical
access, use rights and commercial-readiness states remain separately honest.


## 4. Canonical Content Intelligence

Cross-platform analysis requires one canonical content entity rather than raw platform schemas.

Target semantics:

```text
ContentUnit
- id
- source_artifact_id
- platform
- content_type
- subject_id
- brand_id
- author_id
- host
- guest
- title
- body
- published_at
- runtime_sec nullable
- canonical_state
- provenance
```

Associated canonical objects:

```text
ContentSequence
TranscriptSegment
MetricSnapshot
Evidence
Relationship
ResearchCohort
```

Do not force second-based Runtime semantics onto every platform. `ContentSequence` must support time-based and ordered non-time media.

Shared semantic markers may include:

```text
HOOK
CONTEXT
CONFLICT
TURNING_POINT
EVIDENCE
EMOTION_PEAK
CTA
ENDING
```

## 5. Metric Snapshot Rule

Performance collection is append-only.

```text
MetricSnapshot
- content_unit_id
- observed_at
- views
- likes
- comments
- favorites
- shares
- followers_delta
- per-field truth_state
- source_evidence_id
- collector_run_id
```

Never overwrite prior observations. Never convert missing data to `0`. Preserve at least:

```text
0 / NULL / UNKNOWN / NOT_AVAILABLE / STALE / ERROR
```

## 6. Research and Learning Assets

Research must operate on canonical ContentUnit sets.

```text
ContentUnit[]
→ ResearchCohort
→ ComparativeAnalysis
→ PatternCandidate
→ LearningAsset
```

A 20 breakout / 20 baseline / 20 low cohort is one research configuration, not a hardcoded universal rule.

Pattern states:

```text
DRAFT
EXPERIMENT
SUPPORTED
ADOPT
REJECT
INSUFFICIENT_EVIDENCE
DEPRECATED
```

AI may propose hypotheses, supporting evidence, counter-evidence and candidate patterns. AI must not promote a Pattern to ADOPT by itself.

Learning Assets must be versioned, scoped, evidence-backed and counter-evidence-aware.

## 7. Content Studio Integration

SH-01 Content Studio must close the production chain:

```text
Brief
→ Scoped Retrieval
→ Evidence / Learning Asset Retrieval
→ Draft
→ Fact Wall
→ Review
→ Approval
→ Export
→ Application Trace
→ Evaluation
→ Learning Asset update
```

Scoped Retrieval must use subject, platform, content type, objective, audience and other applicable constraints. Do not dump entire corpora into the model.

Fact Wall must fail honestly. Factual claims require Evidence or explicit Brief input; otherwise return UNKNOWN / unsupported state.

## 8. Application Trace

Every produced artifact must retain which evidence and learning assets affected it.

Target semantics:

```text
ArtifactApplicationTrace
- artifact_id
- brief_id
- subject_id
- platform
- content_type
- objective
- audience
- learning_asset_id
- learning_asset_version
- applied_pattern_ids[]
- applied_pattern_versions[]
- evidence_ids[]
- retrieval_scope
- retrieval_query_hash
- model_provider
- model_version
- prompt_contract_version
- created_at
```

Without Application Trace, the content-learning feedback loop is not considered complete.

## 9. Evaluation Feedback Loop

Published content may later be tracked by Collector. Real MetricSnapshots feed Evaluation:

```text
Artifact
→ External Content
→ Collector Tracking
→ MetricSnapshot[]
→ EvaluationRun
→ PatternEvaluation
→ LearningAsset Version N+1
```

Evaluation result vocabulary:

```text
SUPPORTED
CONTRADICTED
INSUFFICIENT
```

Promotion proposals may be generated automatically, but ADOPT / REJECT transitions must obey permission and approval policy.

## 10. Ownership Boundaries

Shared Capability responsibilities:

- SH-01 Content Studio: scoped retrieval, creation, Fact Wall, review, approval, export, application trace, evaluation linkage.
- SH-02 Evidence Library: unified evidence from upload and Collector, source snapshots, transcript sources, metric evidence.
- SH-03 Canonical Data & Metric Explorer: ContentUnit, ContentSequence, MetricSnapshot and provenance.
- SH-04 Report / Export: research reports, benchmarks, evaluation reports and content performance output.
- SH-05 Learning & Evaluation Assets: patterns, research assets, evaluation, versioning and validation state.
- SH-06 Notification & Task Center: collector tasks, research tasks, approvals, risk, failure, retry and evaluation tasks.

SYSTEM responsibilities:

- Collector Runtime
- Adapter Registry
- Scheduler
- Checkpoint
- Retry / Backoff
- Circuit Breaker / Cooldown
- Health / Recovery
- Permission / Audit integration
- Observability

## 11. Collector Safety Boundary

Collector on logged-in social accounts is permanently read-only.

Allowed: open pages, read public content, legitimate session state, scroll, expand, detect login state.

Forbidden automatic social writes: follow, unfollow, like, favorite, comment, message, publish, repost, profile changes, logout, account switching or equivalent writes.

On CAPTCHA / security verification / IP risk:

```text
Detect
→ Stop Risky Requests
→ Record
→ Circuit Break
→ Cooldown
→ Health Check
→ Resume only after legitimate verification
```

Collector and Publisher are separate capabilities. A future Publisher must use its own permission, approval, effect-fence, audit and legitimate integration path.

## 12. Required Production Contracts

Implementation must reuse existing owners and only add missing semantics. Required capability coverage:

```text
SourceArtifact
SourceSnapshot
CollectorRun
ContentUnit
ContentSequence
TranscriptSegment
MetricSnapshot
ResearchCohort
PatternCandidate
ContentLearningAsset
ArtifactApplicationTrace
EvaluationRun
PatternEvaluation
```

Actual names and storage locations must follow Dependency Trace and current canonical contracts.

## 13. Execution DAG

Codex must execute continuously unless a real blocker exists:

```text
G0  Repository Truth Convergence
G1  DB / Safety Foundation
G2  Source + Evidence Unification
G3  Collector Runtime
G4  Canonical Content Intelligence
G5  Research Engine
G6  Learning Asset Engine
G7  Write / Permission / Approval Closure
G8  Content Studio Production Binding
G9  Application Trace
G10 Performance Collector
G11 Evaluation → Pattern Validation
G12 Learning Version Update
G13 SH-02/03/05/06 + SYSTEM UI Binding
G14 Liangzi-60 Real Acceptance Dataset
G15 Full Regression / Security / Recovery / E2E
G16 Release Gates
→ RELEASED
→ real scheduled feedback cycle
→ OPERATING only after real operating evidence
```

Per gate:

```text
AUDIT
→ DEPENDENCY TRACE
→ REUSE EXISTING OWNER
→ IMPLEMENT
→ MIGRATE IF REQUIRED
→ SCOPED TEST
→ NEIGHBOUR REGRESSION
→ RUNTIME TEST
→ REQUIRED E2E
→ EVIDENCE
→ ONE-PURPOSE COMMIT
→ UPDATE REGISTRY / STATE
→ NEXT GATE
```

## 14. First Safety Gate

Before this closed-loop work touches production writers, Codex must resolve or formally prove safe the current DB-isolation blocker identified as `P0-DBISO-01`.

Until canonical DB override convergence is complete, isolated test / staging execution must respect all currently effective DB override paths and prove the real production DB was not modified.

## 15. Acceptance Dataset

The first full production acceptance dataset is the 60-episode `凉子访谈录` study:

```text
20 breakout
20 baseline
20 low-performing
```

Acceptance chain:

```text
Source
→ Evidence
→ Canonical ContentUnit
→ Transcript / Sequence
→ MetricSnapshot
→ 20/20/20 Research Cohort
→ Comparative Analysis
→ PatternCandidate
→ LearningAsset V1
→ SH-05 visibility
→ SH-01 Scoped Retrieval
→ new content artifact
→ ApplicationTrace
→ Fact Wall
→ Review
→ Approval
→ Export
→ real external performance when available
→ Collector tracking
→ Evaluation
→ Pattern outcome
→ LearningAsset V2
```

Historical and currently available data may complete RELEASED gates. Future feedback windows must not be fabricated. `OPERATING` requires real scheduled feedback evidence.

## 16. Hard Prohibitions

Forbidden:

- second Evidence truth
- second Canonical Data truth
- second Metric Engine
- second Permission system
- second Subject Context
- independent Podcast product
- independent Content Intelligence product
- independent Collector UI architecture detached from SYSTEM Runtime
- Collector output used as unverified AI truth
- UI business-metric recomputation
- overwriting old MetricSnapshots
- missing → 0
- automatic Pattern → ADOPT by AI
- fake future Performance for E2E
- prototype action declared VERIFIED without full evidence
- Collector social write operations
- exposing Cookie / Session / CDP
- deleting real data or muting failures to make tests green
- direct architecture divergence from current Production Truth
- force push

## 17. Release Gates

All must pass:

1. Truth Gate — Remote / Source / Runtime / Registry converge.
2. Data Gate — Upload + Collector reach the same Evidence / Canonical truth.
3. Collector Gate — real collection, dedupe, checkpoint, failure, recovery, risk handling and trace have evidence.
4. Research Gate — real cohort → pattern with supporting and counter-evidence traceability.
5. Creation Gate — Pattern enters SH-01 scoped retrieval and Fact Wall.
6. Application Gate — Artifact traces Pattern / Evidence / Version.
7. Evaluation Gate — real performance can link back to Pattern effect.
8. Production Gate — permission, security, E2E, recovery, regression and DB isolation pass.

If any required gate fails:

```text
PRODUCTION_READY = NO
```

## 18. Real Blockers Allowed to Stop Execution

Codex may stop only for a real blocker such as:

- missing required credential
- inaccessible required third-party source
- destructive production DB operation requiring explicit approval
- legal or security decision that cannot be safely inferred
- unsafe unresolved schema migration conflict
- high-risk external effect requiring real human approval

Large code volume, long tests, context size or number of files are not blockers.

## 19. Canonical Decision

Approved architecture:

```text
Acquire reality
→ preserve Evidence
→ canonicalize
→ research
→ learn
→ create
→ trace application
→ collect real outcomes
→ evaluate
→ version learning
```

Collector remains SYSTEM-owned infrastructure. Shared Capability consumes canonical outputs and closes the research → creation → evaluation → learning loop. No fifth domain is created.
