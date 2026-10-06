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


## 3.2 Product Owner approved universal platform-acquisition convergence — 2026-10-07

This decision refines the existing Collector Runtime without creating a second Collector or lowering current capability.

### Current commercial/R&D boundary

LUMENIS does not currently assume official/partner API authorization for the social platforms. Product closure must therefore continue to prove real data acquisition using legitimately available routes, including Product-Owner-authorized owned R&D accounts, managed sessions/Cookies/CDP/browser workers, public pages, public search/discovery, exact URLs, upload/import and other approved sources. The absence of an official API is a source-state constraint, not permission to replace a complete promised field/capability with a weaker demo.

Future official/partner APIs are provider additions or replacements behind the same connector. They may improve durability, rights, scale or field coverage, but they do not define a new product architecture and must not force consumers to change the Source/Evidence/Canonical contract.

The six current primary platforms (Instagram, Facebook, WeChat Official Accounts, RedNote/XHS, Douyin and X) are the present acceptance baseline only. Bilibili, Weibo, Zhihu, Kuaishou, Channels, YouTube, TikTok, Reddit, LinkedIn and later platforms remain valid expansion targets. A platform source file, schema row or adapter class is not runtime registration or working capability.

### Capability must stay strong while access cost falls

Optimize acquisition cost and recovery effort, not the promised data outcome. For each task, reuse available Canonical observations, public/native sources, discovery/exact-URL resolution, managed authenticated sessions and approved user materials as applicable. Logged-in read-only capability remains available where it supplies fields that zero-auth/public paths cannot currently provide. Do not delete or downgrade proven session capability merely because a public path also exists.

The user-facing product does not expose Cookie/CDP/profile mechanics. During R&D the Product Owner may use their own approved platform identities. When an authorized platform session expires, LUMENIS should recover it inside the controlled product/browser experience and resume only after actual session health is re-read. Future customer/platform identity policy remains separate from the deferred LUMENIS product-account redesign.

### Mandatory P0 convergence before platform-scale work

`COLLECTOR-P0-01 — HK/International XHS recovery fence`

- Production RedNote/XHS recovery must resolve through the current approved HK/International identity/policy/worker (`intl`, RedNote, current production endpoint). The protected Mainland personal identity and historical 9222 recovery path cannot be selected by a production recovery task.
- Generic Auth Recovery and XHS-specific login/keepalive APIs must share this identity decision instead of maintaining conflicting login destinations.
- CAPTCHA/VERIFY and IP/BLOCKED remain different states; neither may be disguised as a login problem.

`COLLECTOR-P0-02 — durable task attempt fencing`

- `dequeue`, heartbeat, checkpoint, ack and fail must bind the same server-issued attempt identity (task + attempt/execution ID + lease owner/run or equivalent opaque completion token).
- A stale/zombie worker from an older lease cannot complete, fail, checkpoint or mutate a newer attempt.
- Reap/retry/DLQ/restart must preserve this invariant.

`COLLECTOR-P0-03 — terminal continuation and durable receipt`

- A client checkpoint is never authorization or durable task truth.
- Query-level continuation and platform-native pagination are separate.
- A server-issued terminal receipt cannot cause completed work/effects to run again. An idempotent terminal replay may return the immutable prior terminal result; otherwise reject it explicitly. Never silently start a new attempt.
- Resume must preserve accepted partial results, failed/deferred pages and exact actor/scope/Permission/source binding.

`COLLECTOR-P0-04 — one ingestion truth`

- Retained `/api/collect`, old V4/root routes, scripts and compatibility callers must converge into the same SYSTEM Collector → Permission → Source → Evidence → Canonical transaction and the same durable task/result semantics.
- `notes` or a platform raw table may remain a compatibility/read model, but a direct notes-only write cannot constitute successful production acquisition.
- Preserve unique legacy behavior until equivalent canonical behavior has tests and runtime evidence; then retire only the duplicate caller/side write.

`COLLECTOR-P0-05 — sole Canonical acceptance`

- `canonical_data` remains the sole current business Canonical truth.
- Tests/gates must reject reintroduction of `zbc_canonical_data` as a required acquisition dual-write. Historical/derived rows may stay readable as provenance only.
- Current main may already satisfy part of this item; fresh source/runtime/tests decide completion and no code should be changed merely to recreate an obsolete assertion.

### Three shared foundations

`COLLECTOR-FND-01 — PlatformManifest`

One machine-readable platform contract owns:

```text
platform/canonical ID + aliases
display/localization identity
native field map + unsupported/unknown semantics
discover/search/detail/comments/replies/creator/media/tracking capability
provider modes: public | managed_session | connector | future_official
adapter binding + runtime registration
session/recovery requirements
raw/canonical mapping
maturity/configured/verified/live states
```

Existing `PLATFORM_ALIASES`, platform capabilities/connection metadata, runtime registry, secondary/primary lists, recovery profiles and UI projections must be generated from or validated against this one contract. No test may depend on import-order side effects to make an adapter appear registered. Adding a platform should normally require the Manifest + Adapter/Provider + recovery recipe + native fixture/contract tests, not edits to many independent lists.

`COLLECTOR-FND-02 — PlatformSession`

One SYSTEM owner projects:

```text
platform
identity_ref
provider_mode
auth_state
verification_state
risk_state
runtime/worker health
checked_at / expiry
recovery_mode / recovery_task
resume binding
```

Cookie/header files, status JSON, in-memory login sessions, browser profile, CDP endpoint and platform-specific keepalive state are implementation details. They may not independently claim `READY`. PlatformSession must distinguish AUTH_REQUIRED, VERIFY/CAPTCHA, BLOCKED/COOLDOWN, worker unavailable and healthy.

`COLLECTOR-FND-03 — LumenisPlatformRecoverySheet`

F/C6 consume PlatformSession/RecoveryTask through one Experience contract:

```text
task continues
→ source reports auth/verify/risk problem
→ RecoveryTask
→ LUMENIS recovery sheet
   ├─ QR scan when the platform supports it
   ├─ controlled login/browser form when QR is unavailable
   ├─ explicit VERIFY handling
   └─ BLOCKED/COOLDOWN state without fake login recovery
→ user completes legitimate platform step
→ server re-reads session/health
→ resume the exact pending attempt/checkpoint
→ return to the original task/context
```

The sheet uses LUMENIS visual language and never exposes Cookie strings, tokens, profile paths, CDP endpoints or raw credential storage. It is a platform connector recovery surface, not the future LUMENIS product-account login.

### Platform expansion exit contract

After P0/foundations, each additional platform must prove at least:

```text
Manifest is registered and truthfully projected
Adapter/provider is callable through the normal runtime without import-order tricks
required session/recovery state is represented
native fields preserve NULL/UNKNOWN/UNAVAILABLE
Source/Evidence/Canonical transaction succeeds
checkpoint/retry/recovery cannot duplicate accepted effects
field/capability coverage is reported honestly
real task result reaches a CTH/BMP/Shared consumer
```

Do not call a skeleton, schema, file presence or planned adapter a working platform. Do not block unrelated working platforms when one source is unavailable.

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
