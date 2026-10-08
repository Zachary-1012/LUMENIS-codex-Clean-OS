# LUMENIS Global Product Universe / Focus Context / Data Maturity — CURRENT

> Status: **CURRENT SUBORDINATE CONTEXT AND DATA-MATURITY CONTRACT**
>
> Approved by Product Owner: 2026-09-21
>
> Authority boundary: subordinate to the sole Product Architecture, Source Owner Index, Permission, Evidence, Database, Collector/Browser, AI Gateway and Experience Constitution owners. This contract defines shared semantics and acceptance; it does not create another Subject/BrandFocus, database, Evidence, Permission, collector, AI or UI owner.

This contract governs exactly one internal full-universe edition: `ONE Product`, `ONE Repository`, `ONE Product Core`, `ONE Global Product Universe`, `ONE Canonical Data`, `ONE Evidence`, `ONE Permission`, `ONE Context Model` and `ONE Experience Ecosystem`. Its coverage rows are acceptance dimensions of the same product, never separate products, versions, repositories, entries, release tracks or truth stacks. Future customer/workspace/role/entitlement/source/compliance restrictions remain access policy over this same product truth.

## 1. Canonical model

```text
GLOBAL PRODUCT UNIVERSE
├─ global commercial-entity universe for CTH
├─ global brand-entity universe for BMP
├─ legally collected real signals, relationships and business-domain content
└─ authorized on-demand capabilities and separately opted-in background work
          ↓
select Subject / BrandFocus
          ↓
change only the current focus context
          ↓
Visibility / Permission / Commercial Policy decides what is visible and actionable
```

The default product context is `GLOBAL / ALL`. It is neither a blank workspace nor a fixed Subject or BrandFocus. CTH and BMP share the Global Product Universe discovery/context foundation while retaining separate business semantics, metrics, relationships, workflows and owners.

Selection is not authorization and is not a runtime control. Selecting or clearing a Subject/BrandFocus must not start, stop or authorize Collector, Browser, AI, content, report or background-task execution. On-demand work runs only after its explicit request; any opted-in background work remains independent of focus and within its configured, source-authorized and permitted scope.

### Collection mode — Product Owner decision, 2026-09-27

The default collection mode is `MANUAL`: a user explicitly clicks to request a bounded collection for an identified, authorized scope and source. `AUTO` is off by default, including when no prior mode has been saved. It may run only after the user deliberately enables it for a reviewable scope, source set and cadence through the existing SYSTEM Collector, source authorization, actor Permission and effect boundary. The user can turn it off; disabling prevents future scheduled collection without rewriting already captured Evidence. Registration, search, focus selection, clear focus, opening a page and startup never silently opt a user into automatic collection or trigger a manual request.

The prelaunch Global baseline still requires real, traceable CTH and BMP data before a customer arrives. Authorized operators may build and refresh it through explicit manual collection; an explicitly enabled automatic schedule may maintain an authorized portion. Show the actual collection mode, last attempt, freshness, source limits and `NOT_COLLECTED`/`STALE`/`BLOCKED` states. Do not claim continuous freshness where no active schedule or verified manual refresh supports it. This mode decision changes the trigger policy, not the one Source → Evidence → Canonical owner chain or the requirement that focus never controls collection.

Clearing focus returns to `GLOBAL / ALL`. Every result, Evidence reference, AI task, content/report artifact and consequential action must carry its actual scope. A client-supplied header, route parameter, selected card or local UI state never grants access.

### GLOBAL work and product-owned acquisition — 2026-10-03

No Subject/BrandFocus selection is required merely to enter work or submit a valid GLOBAL/ALL task. Resolve the actual actor and explicit global scope on the server, retain fresh permissions and each original source's exact entity/domain/market/purpose binding. Focus is an optional narrowing; Clear returns the active view to GLOBAL without rewriting saved task, result, Evidence or Artifact scopes. An unbound callable or source grant remains that specific gap, not a reason to invent a subject/login wall.

SYSTEM Collector/Browser code owns search input, navigation, permitted scrolling, parsing and capture; SYSTEM Scheduler owns due-only maintenance, bounded retry and restart recovery. Development harness execution is CODE_EXECUTED_BY_DEVELOPER_TRIGGER, not unattended product operation. Assisted web discovery/import remains labelled assisted and cannot pass autonomous platform collection.

For approved prelaunch public-baseline AUTO, prove an actual future due cycle with Codex/CUA/manual developer triggers absent: append/change/no-change semantics, Source/Evidence/Canonical lineage, last attempt/success/freshness, partial failure and recovery remain correct. Clock simulation/immediate replay proves technical behavior only; real elapsed scheduled operation is separate. Final-user AUTO remains explicit opt-in; MANUAL remains default. Login expiry requests a real human login through the existing session owner; it never accesses the protected Mainland personal account.

Discovery uses authorized real observations: distinguish comparable measured trends, corpus-observed hotspots, an actual official platform rank and owned-AI suggestions. Preserve platform-specific fields, publication/capture/event/window/derivation times, sampling and coverage. Absent fields or unmeasured time buckets are unknown/unavailable, not zero or an invented trend. Related-work selection is not permission to reuse, export, publish or train.

## 2. Existing owners and compatibility boundary

| Concern | Sole current owner | Contract boundary |
| --- | --- | --- |
| Product and domain meaning | `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` | CTH is Subject-first; BMP is Brand/Market-first; neither becomes the other. |
| Context execution | current `subject_context.py` / domain context callers until explicitly converged by their scheduled owner round | Must evolve toward explicit `GLOBAL / ALL` and focused context without creating a second context service. |
| Entity identity and discovery | existing `subject_registry.py` and scheduled canonical registry/database work | Directory membership or discovery is not Permission and does not prove collected data. |
| Canonical persistence | `lumenis/shared/database/` and `data/monitor.db` contract | Global registry, focus keys and business data must not be faked through one default row or a second database. |
| Source and Evidence | SYSTEM Collector/Browser plus `lumenis/shared/evidence/` | Source authorization, capture, Evidence and Canonical Data remain traceable and separate from focus selection. |
| Permission | existing account/authorization and SYSTEM Permission owners | Internal Product Owner/Admin full audit and commercial-customer visibility require explicit, auditable policy; no hard-coded key or bypass. |
| Surfaces | one Product Core/API/ViewModel consumed by approved Website/Web/Desktop/Mobile roles | Surfaces display and change focus; they do not own context, Permission or data truth. |

`GUANGZHOU_TAIKOO_HUI / 广州太古汇` is the controlled depth-reference Subject across all relevant rounds. It is not the product default, not `GLOBAL / ALL`, not a substitute for the global universe, and not proof that global CTH or BMP data is mature.

Current source still contains legacy CTH compatibility fallbacks to `GUANGZHOU_TAIKOO_HUI`. ROUND 02 classifies those values as protected compatibility behavior only. Consumers must not reinterpret them as the default product truth. Behavioral migration belongs to the scheduled database/context/permission/surface rounds and must preserve protected CTH behavior while removing implicit defaulting from global product entry.

## 3. Honest states and add/search semantics

Users may discover, search and add any commercial entity or brand entity supported by the product contract. Adding an entity means a controlled path through entity registration/identity resolution, source configuration and authorization, acquisition state, Evidence and Canonical Data. It never means generating synthetic content.

The Subject/BrandFocus selector serves the Global Product Universe, not a Guangzhou Taikoo Hui allowlist. CTH must support discovery/search/add/select for global commercial entities; BMP must support the same for global brand entities. A selectable identity carries a stable canonical ID plus sufficient type, region, industry and relationship metadata for disambiguation. Duplicate merge and identity-conflict handling remain explicit canonical-registry operations, never silent UI aliasing.

Entities without usable data remain discoverable with an honest state:

```text
NOT_COLLECTED | COLLECTING | NOT_CONFIGURED | BLOCKED
```

Keep these distinct from `READY`, `0`, `NULL`, `UNKNOWN`, `NOT_AVAILABLE`, `STALE`, `OFFLINE` and `ERROR`. The `GLOBAL / ALL` entry may prioritize entities, signals and content that meet the applicable data-maturity gate; it must not imply that every world entity has complete data or mix immature entities into the same ready state.

### Mandatory user-added Subject / BrandFocus path at closure

`LUMENIS_INTERNAL_FULL_UNIVERSE_READY=YES` requires a real user-initiated add path for both a CTH Subject and a BMP BrandFocus. Each path must use the same canonical identity resolution, deduplication/conflict handling and region/industry/relationship metadata, then pass identity/source authorization and actor Permission before explicit manual acquisition or separately enabled scheduled acquisition, Capture, Evidence, Canonical Data binding, and a user-visible result/recovery path. Adding an identity does not grant Permission or silently start collection. A registration-only row, fixture, or selection-only test is not closure evidence.

### Best-effort partial collection and time semantics

Authorized collection may return a useful partial result, but it must identify each missing or failed source/entity/signal, its last attempt outcome, and whether a retry is `PENDING / SCHEDULED` with the existing next-attempt evidence or is not scheduled and why. Preserve the applicable `NOT_COLLECTED`, `NOT_CONFIGURED`, `BLOCKED`, `STALE`, `OFFLINE`, `ERROR` and retry states at their actual scope. Never represent an unavailable portion as zero, empty success or AI-filled fact; report real measured zero only when the source measured zero.

Keep `captured_at` and `collected_at` according to their existing owner-specific meanings, distinct from `published_at` (source publication time), `occurred_at` (real-world event time), the metric/trend window, and `derived_at` (calculation time) throughout Evidence, Canonical Data, APIs, reports and acceptance evidence. Do not substitute one for another. If source time is absent, retain `NULL / UNKNOWN`; do not infer it from capture, collection, publication, current time or a neighboring event.

## 4. DATA_MATURE minimum contract

Record count, a non-empty page, a global directory, a few connected platforms or one successful Subject is never sufficient. For the active round and capability slice, `DATA_MATURE` requires auditable evidence that:

1. entity identity and relationships are disambiguated; Subject/Brand ID, name and business domain are traceable;
2. source legality, authorized purpose, collection state and capture time are explicit;
3. Raw Capture → Evidence → Canonical Data IDs, owner, timestamp and scope are traceable;
4. freshness, coverage, missing/not-collected/failure and numeric zero are distinct;
5. metric definition, denominator, time window, source and computation owner are explicit;
6. at least one real user path uses the data to finish the round's job rather than only rendering cards;
7. continuous operation, failure recovery, rollback and data-quality evidence meet the round's responsibility;
8. fixtures, mocks, manual database injection and AI-invented content are not presented as mature production data.

Global maturity additionally requires an approved, auditable coverage matrix for regions, languages, industries and sources, freshness SLA, Evidence coverage, entity-disambiguation/relationship quality, data quality, continuous operation, recovery and an extensible add-entity path. Uncovered entities remain honest and enter the add/collection workflow; the product must never claim complete data for every world entity without executable evidence.

### Baseline inclusion and completion gate — acceptance specification v1.0.0

Before either global coverage dimension may be `YES`, the existing canonical registry/Evidence owners must support a completed baseline inventory of globally influential brands (BMP) and major representative commercial venues (CTH), together with an immutable, Product-Owner-approved inclusion-rule version. The rule must define its declared regions, industries and venue classes; named source and edition/reference window for each population; measurable inclusion/exclusion and tie rules; identity, alias, relationship and deduplication handling; corroboration requirements; refresh/review cadence; and the applicable legal/commercial use boundary. The inventory must enumerate every qualifying entry under that rule with its canonical identity, region, industry/type, relationships, Source/Evidence provenance, observation time and honest collection/maturity state. It remains inside the existing canonical registry and Evidence owners; it does not create a second baseline store.

An entity sample, random sample pass, fixture, or selected reference Subject validates only the sampled records against the declared baseline. It never defines or completes the baseline population, inclusion rule, or global coverage denominator. A missing source, unapproved threshold, incomplete region/category, unresolved duplicate or unverified list leaves the relevant global dimension `NO / NOT VERIFIED`. Here `v1.0.0` versions this acceptance specification only; no Product-Owner-approved entity inclusion-rule version or completed baseline inventory is asserted, and the current coverage values below remain unchanged.

Product Owner 2026-09-29 adjustment supersedes the 2026-09-27 equal-country **50 distinct commercial Subjects and 50 distinct BrandFocus identities** expansion target: reconcile and finish the country candidates already produced, but prioritize excellent, regional, specialist and niche entities operating in China, with a disclosed global reference population. Preserve separate CTH/BMP navigation categories for China, South Korea, Japan, United Kingdom, France, United States, Canada, Australia, Malaysia, Singapore, Thailand, Brazil, Norway and `OTHER`; no silent loss of existing country research or identities. One entity may legitimately appear in multiple operating markets, but each country membership needs its own Evidence-backed relation; headquarters/origin, legal jurisdiction, operating market, marketing activity and venue location remain different roles. `OTHER` groups evidenced countries outside the 13 named categories and is never stored as an ISO country. Counts alone do not establish source rights, current operation, quality, freshness or Global coverage. The revised priority does not self-approve an inclusion-rule version, completed inventory or coverage PASS.

Global baseline construction and real CTH/BMP jobs run concurrently. A job may proceed when its task-specific real data has clear provenance, correct scope and enough coverage to support the requested result; a complete country/global inventory is not its prerequisite. Guangzhou Taikoo Hui, Shenzhen Luohu MixC, Nike and Le Labo remain representative jobs, never substitute Global coverage. Each path verifies interruption, bounded retry, revocation, honest failure, result reopening and applicable restart recovery during its own implementation; ROUND 15 adds cumulative cross-system/cross-surface release recovery and rollback.

For the Product Owner's own prelaunch Global public baseline, explicitly approved public sources may have an automatic, freshness-aware maintenance schedule through the existing SYSTEM Collector/Scheduler owners. This approval excludes account data, private Cookies/sessions and unapproved platforms; a source without explicit approval fails closed. Final-user collection continues to default to `MANUAL`, and `AUTO` requires that user's explicit opt-in. Focus selection never triggers either mode.

### PRE-LAUNCH GLOBAL FOUNDATION

The mature global foundation exists and refreshes before customer onboarding. A customer's first search, selection, purchase or workspace entry must not be the product's first collection, first entity registration or first creation of baseline data. Before release, the same one Product must already provide the approved versioned inclusion rule and completed baseline inventory required above, plus:

- a continuously maintained canonical global commercial-entity and brand-entity registry/index with stable IDs, aliases, type, region, industry/domain, relationships and controlled deduplication/disambiguation;
- authorized CTH/BMP sources, explicit manual acquisition, individually approved automatic maintenance for the product's own prelaunch public baseline, and only opted-in automatic schedules for final-user scopes, with Evidence lineage, freshness and quality states established before a customer arrives;
- a `GLOBAL / ALL` entry with real, mature and traceable product content rather than a fixture, empty shell or wait-for-customer placeholder;
- honest incremental onboarding/acquisition for new, long-tail or source-restricted entities as extension of the mature base, with real state and source limitations rather than an invented complete profile.

Commercial customers later apply Workspace/Role/Entitlement/Source Authorization/Compliance visibility and action policy to this same mature product truth. They do not trigger or receive a second customer-specific data truth.

### Measurable maturity matrix

Every owning round defines and verifies thresholds appropriate to its slice from current source, real runtime and real data samples. At minimum the matrix reports `coverage`, `freshness`, `completeness`, `provenance/Evidence`, `deduplication/entity resolution`, `source authorization/compliance`, `failed/stale/blocked ratios` and `CTH/BMP workflow usability`. Counts, “many records”, HTTP 200 or page non-emptiness do not satisfy a threshold. Thresholds must state numerator, denominator, population/scope, window, source, owner, sample method and failure condition.

## 5. ONE INTERNAL EDITION ACCEPTANCE MATRIX

The following are three supporting coverage dimensions of one internal edition. They must be advanced and evaluated separately for diagnostic honesty, but they never become separate products, releases, databases, APIs, permissions, contexts, surfaces or delivery plans:

| Gate | Required proof | Current baseline at ROUND 02 |
| --- | --- | --- |
| `Global Commercial Coverage` | Global commercial-entity universe, including the completed major-venue baseline under the approved versioned inclusion rule, relationships, industries/domains, legal sources, acquisition coverage, signals, Evidence, Canonical Data, freshness, quality, continuous operation, recovery and the mandatory user-added Subject path meet the approved delivery threshold. | `NO / NOT YET VERIFIED`; ROUND 02 establishes authority and consumer semantics only. |
| `Global Brand Coverage` | Global brand universe, including the completed globally influential-brand baseline under the approved versioned inclusion rule, plus authorized market, competitor, creator, channel, content, propagation, campaign and evaluation data, and the mandatory user-added BrandFocus path, meet the same auditable threshold. | `NO / NOT YET VERIFIED`; ROUND 02 establishes authority and consumer semantics only. |
| `Guangzhou Taikoo Hui Reference Coverage` | `GLOBAL / ALL` → locate/add/focus/clear → Source → Capture → Evidence → Canonical Data → applicable CTH/BMP workflow → AI/content/report/action → Outcome → Evaluation/Learning → Return, with other configured work continuing. | `NO / PARTIAL`; controlled test identity exists, but the complete loop is not implemented or accepted. |

Only when all three coverage dimensions are `YES`, the approved rule and both baseline lists are complete, and the user-added Subject and BrandFocus paths pass the full real-data chain above, may Sol set the single top-level conclusion:

```text
LUMENIS_INTERNAL_FULL_UNIVERSE_READY = YES
```

If any dimension is `NO`, `PARTIAL`, `BLOCKED` or `LIVE_UNVERIFIED`, the single conclusion is `NO` and the exact blocker must be named. A single-subject E2E, non-empty UI or catalog presence cannot substitute for either global coverage dimension. This conclusion is evaluated before the Real Delivery Overlay's final seven statuses; it does not create an eighth status or a second product release.

The `YES` conclusion additionally requires cross-Subject selection/workflow validation and continuous refresh/recovery to pass on the same release candidate. “Global” means the approved and disclosed coverage scope backed by authorized sources and measurable evidence; it never means an unprovable claim that every entity in the world has complete data.

## 6. Per-round responsibility

| Round | Required incremental responsibility |
| --- | --- |
| 02 | Fix this single semantic owner, consumer contract and compatibility routing. Classify Guangzhou Taikoo Hui fallback as compatibility, never global truth. Add the three-line impact to Charter/Delivery Card; do not claim data maturity. |
| 03 | Separate Global entity registry, focused-context keys and canonical data/migration boundaries; no synthetic default record. Prove protected-data safety and rollback. |
| 04 | Implement `GLOBAL / ALL` visibility, controlled internal audit, commercial customer scope, and strict separation of focus from Permission. |
| 05 | Runtime and recovery remain independent of UI focus; runtime observations carry actual scope where applicable. |
| 06 | Collector/Browser execute explicit authorized manual requests and separately opted-in automatic schedules independent of focus, closing Source → Capture → Evidence → Canonical Data for relevant global matrices and the reference Subject. |
| 07 | AI/Agent/Shared outputs carry actual scope; no AI-created truth; evaluation/learning preserves lineage and Permission. |
| 08 | Four-surface contract implements default `GLOBAL / ALL`, search/add/focus/clear/restore interactions without a hard-coded test Subject. |
| 09 | Golden Pages execute Global → Focus → Return with honest data states and reference-Subject evidence on applicable surfaces. |
| 10 | CTH monitoring/analysis advances global CTH coverage and the reference Subject's source-backed signal/Evidence path. |
| 11 | CTH case/decision advances the reference loop through outcome, report/export and Return while preserving global CTH maturity evidence. |
| 12 | BMP portfolio/market advances global BMP entity/relationship/market/competitor/creator maturity and applicable reference relationships. |
| 13 | BMP content/campaign/evaluation advances authorized content, channel, propagation, campaign, outcome and learning maturity. |
| 14 | Remaining ACC/AI/Shared/SYSTEM experiences preserve Global → Focus → Return, honest states, scope, manual-default control and independence of any opted-in background operation. |
| 15 | Revalidate all three lines on the exact release SHA across promised surfaces and commercial/release gates; verify the approved versioned inclusion rule, completed brand/venue baseline inventories, and both formal user-added Subject and BrandFocus paths through identity/source authorization + actor Permission → explicit manual acquisition or separately opted-in scheduled acquisition → Capture → Evidence → Canonical Data → result/recovery. It may not implement accumulated obligations from prior rounds. |

## 7. Per-round acceptance block

Every relevant Round Charter and `REAL DELIVERY CARD` includes `GLOBAL UNIVERSE / DATA MATURITY IMPACT` with:

- `GLOBAL CTH maturity impact`;
- `GLOBAL BMP maturity impact`;
- `Guangzhou Taikoo Hui reference-loop impact`;
- in-scope responsibility, verified evidence, still-immature facts, exact next owner/round and non-blocking unrelated work;
- current values of the three supporting coverage dimensions and `LUMENIS_INTERNAL_FULL_UNIVERSE_READY`.

The one-edition selector acceptance matrix is:

| ID | Required acceptance |
| --- | --- |
| A | Global Subject/Brand discovery and selection works through the canonical owner. |
| B | At least one non-Guangzhou-Taikoo-Hui commercial Subject and one non-Guangzhou-Taikoo-Hui brand Subject complete honest selection/state validation; uncollected entities enter onboarding/acquisition rather than receiving synthetic data. |
| C | Guangzhou Taikoo Hui completes the deep reference workflow required by the active round. |
| D | Clearing selection restores `GLOBAL / ALL` without starting or stopping any separately opted-in background capability. |

If current source, fixtures, APIs, ViewModels or UI hard-code Guangzhou Taikoo Hui as the sole selectable/default Subject, the round records a real gap and assigns it to the owning scheduled round. A fixture pass is not global selector capability.

## 8. RANDOM ENTITY DATA ACCEPTANCE

Controlled prelaunch comparison identities are Guangzhou Taikoo Hui (deep CTH reference), 罗湖深圳万象城 / Luohu Shenzhen MixC (additional CTH venue), Nike and Le Labo (BMP brands). 深圳万象天地 is a different venue and must not substitute for 罗湖深圳万象城. These named exercises supplement the rotating, cross-region random sample; they neither define the approved global baseline nor prove its coverage. Record each identity, region/type, actual collection and Evidence state, Global → Focus → Clear behavior, and honest missing/failure/time semantics.

Every context/data/collector/AI/content/report/API/ViewModel/surface/workflow round performs a reproducible rotating sample from the canonical global registry. Sampling is stratified by region, industry, entity type and freshness; it includes Guangzhou Taikoo Hui as the fixed deep reference plus rotating non-reference commercial and brand Subjects and cross-region samples. Fixtures and a fixed all-Guangzhou set are forbidden as live acceptance.

For each sampled entity, the applicable real path is:

```text
GLOBAL / ALL → search/discover → select Subject/BrandFocus
→ page/ViewModel/API → Canonical Data → Evidence Trace
→ the round's real business result
```

An entity already classified covered/mature must not produce silent blank, all-zero, missing→0, placeholder or invented content. Such a defect makes the relevant round `REWORK` or `BLOCKED` until fixed and resampled. A new, long-tail or restricted entity still returns real identity, stable ID, coverage/freshness, source/Permission limit, acquisition state and canonical onboarding path.

Each round preserves a reproducible evidence record containing sampling seed, selection query/strata, sample IDs, timestamp, data/schema/capability version, request and applicable real-surface evidence, Evidence IDs, expected/actual result and failure reason. Samples rotate and cumulative coverage is reported. For a promised page, API 200 or fixture tests alone do not count.

Every related Round report includes:

```text
RANDOM ENTITY DATA ACCEPTANCE
sample seed / sample count / sample IDs
non-empty valid result rate
stale / blocked / failed rate
Evidence trace rate
empty-state defects
maturity delta since prior round
```

If the canonical registry or required maturity fields do not yet exist, record `sample count = 0`, `NOT YET IMPLEMENTED` and the exact owning round. Never manufacture a sample or percentage. Report sample counts separately from the approved baseline's total and covered counts; passing a sample cannot satisfy the baseline inclusion or completeness gate. ROUND 15 expands and revalidates cumulative coverage; it is not the first random inspection.

The round also evaluates, only where its owned slice can honestly do so:

1. enter `GLOBAL / ALL` without fabricating worldwide completeness;
2. search/add a Subject or BrandFocus through the canonical path;
3. focus Guangzhou Taikoo Hui as the controlled reference path;
4. prove correct scope on results, Evidence, AI tasks and reports;
5. clear focus and return to `GLOBAL / ALL`;
6. prove selection grants no Permission;
7. distinguish no data, not collected, not configured, blocked and denied;
8. prove manual collection requires an explicit click, automatic collection remains off until deliberately enabled, and any opted-in background work continues independently of focus.

Unavailable later-round functionality must be recorded as `NOT IN ROUND / NOT YET IMPLEMENTED`, not simulated and not allowed to block unrelated work. A relevant round cannot claim its own contextual responsibility complete without its required proof.

## 9. Baseline-source research — accessed 2026-09-26

| Candidate | Version / maintenance evidence | License and service boundary | Decision and owner mapping |
| --- | --- | --- | --- |
| [Wikidata structured-data downloads](https://www.wikidata.org/wiki/Wikidata:Database_download) | Official download page, last edited 2026-04-09 (revision `oldid=2479770906`); JSON/RDF are documented stable interfaces; full JSON is weekly and add/change dumps cover the previous 24 hours. No specific dump snapshot is pinned here. | Main, Property, Lexeme and EntitySchema structured data are CC0 and may be used commercially and offline; other namespace text and media have separate terms/licenses. | `ADAPT` as a candidate identity cross-reference through the existing SYSTEM Collector → Source/Evidence → Canonical Data owners after snapshot/version and lineage review. Wikidata IDs do not establish brand influence, venue representativeness, or Production Truth; corroborate baseline claims with approved primary sources. |
| [Wikidata Query Service User Manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual) | Live official service documentation accessed 2026-09-26; no immutable service release or dump snapshot is pinned, and limits may change. | Public endpoint documents a 60-second query deadline, 60 seconds processing per 60 seconds per client, 30 error queries/minute, five parallel queries per IP, and HTTP 429 with `Retry-After`; a compliant identifying User-Agent is required. | `DEFER` as the required baseline acquisition path. If a bounded query is later justified, use the existing Collector with those limits, backoff, provenance and honest retry state; prefer versioned dumps for baseline population. |
| [Wikidata Query RDF GitHub mirror](https://github.com/wikimedia/wikidata-query-rdf) | Accessed 2026-09-26; the repository identifies itself as a GitHub mirror and says the actual code is hosted on Gerrit. No immutable upstream commit/release was pinned in this review. | README identifies `blazegraph` and `war` as GPLv2, while `tools`, `common`, `testTools` and `dist` are Apache-licensed; this is not one uniform package license. | `DEFER` self-hosted WDQS as a product dependency. Dataset CC0 does not transfer to query-service software; any future self-hosting decision requires pinned upstream source, module-level license/security review and an approved SYSTEM deployment path. |
| [OpenStreetMap Foundation Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) | Live policy page accessed 2026-09-26; no fixed version is published and the policy may change without notice. | ODbL imposes attribution/share-alike obligations on adapted databases; the public service has a maximum of one request/second, requires an identifying User-Agent/Referer and attribution, discourages periodic/bulk use, and forbids systematic POI/list extraction. Commercial users must account for policy changes and service withdrawal. | `DEFER` as a global baseline source. It is not a complete venue inventory. Any bounded geocoding use must pass a deliberate commercial/license review and route through the existing acquisition owner with caching, rate limits and attribution. |

Research adds no dependency or new owner. Source/service status, terms, and version pins must be rechecked when a source is actually selected; no source availability or baseline coverage is claimed by this table.


## 10. Task-semantic vocabulary and continuous acquisition

Six primary platforms are Instagram, Facebook, WeChat Official Accounts,
RedNote/XHS, Douyin and X. C1 begins/resumes actual eligible acquisition routes
for all six; names/registrations/imports are not proof of platform collection.
Keep other existing platforms. Every platform has its own native fields, access
state, permitted identity, exact entity/domain/market/purpose and Evidence path.
Missing access/binding blocks that portion honestly while available platforms
continue, without substituting a differently scoped account or fake zero.

Through existing SYSTEM Collector/registry/Source/Evidence/Canonical owners,
maintain versioned topic terms per platform and canonical brand/commercial
entity. Record observed tag/phrase, source URL/ID/Evidence, original language,
aliases, actual city/store/venue, source/observation times, applicable scope,
ad/organic and official/consumer distinctions, permitted use and review state.
One spelling never resolves same-named venues or cross-city stores by itself.
No second topic database, scheduler, registry or collector is authorized.

Compile purpose queries from the actual user task, accepted source vocabulary,
canonical aliases, topic dimensions, language, time and scope constraints, with
explainable inclusion/exclusion and disambiguation. A composed query is derived
task text, not an observed platform hashtag/hotspot/ranking. Do not invent terms
as platform facts or guess an entity, popularity, advertisement status or date.
Relevance and exact-scope checks must reach real capture/intake and the consumer
job, not stop at a query-plan candidate. Unknown/conflicting bindings stay honest
while the owner resolves them; useful authorized results remain the real exit.

The user explicitly opted this internal approved program into continuous operation.
The 2026-10-08 correction removes the former universal publication-start date.
Acquire by authorized subject/topic and task semantics with bounded budgets,
then classify/order/filter by genuine source publication and event time.
An explicit user/task time range still constrains its query; no global earliest
date is inferred when none was requested, and this is not unlimited historical crawling.
Retain source timezone/date precision and normalize by the current time owner;
capture/import/refresh time cannot replace source publication/event time.
Unknown publication/timezone and unsupported history windows remain explicit
coverage gaps, never in-window proof, all-zero buckets or silent omissions.
Keep all older evidence intact and eligible for its actual authorized task; historical
material is not excluded merely because it predates a global calendar cutoff.

Persistent product Scheduler/Collector own backfill cursors, per-platform window/
progress, incremental watermark, last attempt/success, next due cycle, bounded
Retry-After/backoff, idempotence and restart/overdue recovery. Rotate the six
platforms if needed. Training, development, rule publication or another task
must not cancel their resident acquisition schedule or make collection depend
on Codex/CUA. Source challenge/outage/revocation safely isolates only the
affected path; continue eligible others, retain pending gaps and resume it after
actual recovery. Never defeat access controls to satisfy 'continuous'.

Existing MANUAL future-user defaults remain; this is explicit AUTO consent for
the named internal program and current approved exact identities/scopes, not an
unbounded consent for all accounts. Protect the personal Mainland XHS profile;
resolve other platform sessions through registered secret-safe owners. Prefer
official permitted APIs/refresh/session continuity and researched legitimate
recovery to repeated human troubleshooting. Historical R-0003/R-0004 and their
MediaCrawler/xiaohongshu-mcp/Spider_XHS references are research inputs only;
recheck versions/licenses/current rules and do not activate legacy accounts,
rotating identities, CAPTCHA bypass or presumed immunity to platform bans.
After a user reports verification complete, the session owner reads back actual
authorized state and resumes only the pending scoped work.

Acceptance requires real topic/task coverage and explicit requested-window receipts/gaps,
topic/task→query→Capture→Evidence→Canonical→useful normal business result,
repeated due cycles while another job runs, one-platform failure isolation and
restart recovery. Mocks, replay clocks, a name search, raw posts, imported rows
or a live schedule registration alone cannot prove these. C1 retains continual
China/global brand/commercial-entity additions and relation review alongside
real task validation, without waiting for complete global directory coverage.


### User-reviewed foundation vocabulary seed

Use the user-reviewed xujing_topic_seed_100_4confirmed_20261004 XLSX/CSV/JSON as
versioned foundational test entity/topic inputs through existing Source/registry/
Evidence/Canonical ingestion, then real runtime queries. JSON has100 topic
records and41 source records; four named entities have25 terms each. Its own
metadata remains4/6 entities confirmed,2 unnamed and100 heat UNKNOWN, with no
verified hotlist. User review approves this input, not fabricated platform
hotness, rankings, complete six-platform coverage or automatic MODEL_TRAIN use.
Preserve term IDs, entity/type, topic/observed_literal/term_type/association,
platform, source IDs/URLs/titles, publication literal/capture/review times,
evidence level, heat/null/rank, recommended use, notes and evidence locators.

Original files and original terms are immutable and never deleted. Add versioned
terms and associations based on actual time, commercial entity, brand, activity
and event changes, with reason/provenance/effective interval/parent version;
retain old terms for search/history/rollback. Active query views select applicable
versions and mark retired/expired/conflicting terms without destroying them.
C1/W6 store/resolve/import this reviewed source through current owners and ensure
packaged deployment/runtime uses its admitted version rather than a developer's
attachment path or a fixture. Preserve current exact identity/source-use checks,
normal explicit authorization and honest unknowns without asking for another
manual review of the same100 terms. This seed does not limit ongoing entity/
source/topic growth or replace whole-universe data coverage.

### Topic growth and two heat meanings — latest C1 human correction, 2026-10-04

The Product Owner explicitly prioritizes sourced topic growth over current heat/
rank positions. Expand existing terms plus new time/entity/brand/activity/event
terms across additional brands, commercial entities and platforms; the four
seed subjects and six primary platforms are baselines, not permanent limits.
Use C1's newly sourced terms through this same versioned owner chain. Hotlist
verification is not a prerequisite for vocabulary growth or actual collection.

Keep LUMENIS corpus-derived heat separate from platform-provided heat/rank.
The former needs a declared corpus/window/scope/sample/metric/version and actual
data; the latter needs the actual platform-native field/source/window. They are
not interchangeable, and unknown remains unknown. Greater data volume alone
does not prove representative global demand. Retain original terms/versions,
sources/times and controlled updates; do not delete or invent heat values.


### Retained TopicCampaign safety parameters

The approved original 100-term/41-source seed is packaged unchanged at
`config/collection-topic-seed-20261004.json` (SHA256
`cfe3b6cb424ee0efe3d917479ba95db66f4ca9b8df32fa891fcf16fd6c576028`).
`acquisition_plan.load_approved_topic_seed` reads that product file, not a
developer attachment or work directory. Seed-bearing business requests must
match its topic ID, source ID/URL, original literal, term, platform and registered
entity. The explicit user task selects purpose and facets; packaging grants no
trend status, entity promotion, source-use permission or model training.
Retain this original when adding subsequent source-backed topic versions.

These seed checks apply to requests explicitly referencing that seed. They do
not require every subject-scoped collection batch to await all 100 terms or
post-intake keyword analysis; the current C1 priority below controls that order.

The existing platform-collection search API accepts task-selected
`business_requests`, bounded `max_queries` and a checked plan continuation.
It resolves the actual actor/scope; a client cannot upload a completed-checkpoint
claim to skip collection. Scheduled internal purpose requests use the existing
signed baseline loader, fresh Permission check of the whole query and request
bound, then the same Collector transaction. This is not a parallel scheduler or
an automatic grant to future-user AUTO. Live platform/session/continuity evidence
remains required separately from source integration.

The 2026-09-03 TopicCampaign exception remains source-specific history and
configuration: hours [9, 11, 13, 15, 17, 19], staggered execution, maximum eight
runs including manual on its own counter. Retiring TWIN_EXECUTION_GATE does not
change those code values or authorize unrestricted collection. These values do
not impose a universal twice-daily limit on the current continuous multi-platform
program. Current schedules require source identity, approved policy, bounded
retry/cooldown, observable outcomes and recovery through the existing Scheduler.
No new module starts collection implicitly; actual risk/authorization failures
stop only the affected path and preserve evidence for recovery.

### 2026-10-08 维度完整、真实缺失与采集能力闭环

Product Owner明确取消“所有数据必须采全”的要求。产品必须保留业务需要且定义准确的维度，但不承诺平台未提供、无权访问或客观不存在的数据。完整基线名录/主体关系与每个主体每个字段100%有值是不同要求；本节不取消已批准主体/品牌登记、真实采集能力、六平台接入责任、持续运行和有效业务成果。

维度沿现有Metric/Truth Table/ViewModel定义其名称、含义、单位、范围、时期、来源和可比条件；缺值仍展示该维度及“—”，可查看具体原因和最后实际核验时间。展示层横杠不进入Canonical作数值，API/存储保留null及当前状态/原因。真实0仍显示0，未采集、未提供、权限受限、失败、过期、部分、未知和不适用不能混成同一事实。不把缺值维度隐藏，不用抓取时间冒充发布时间，不以旧值冒充新值。

只有对应能力在真实授权来源上走通 query→fetch/parse→Source/Evidence/Canonical→用户可见结果→刷新/取消/恢复并有同版本回执，才能把仍缺失的字段归因于已核实的来源限制。对确实不可接入的平台保留BLOCKED/原因，不把其他平台成功当它的闭环。程序解析缺陷、接口未接、没有执行、权限过期或未知原因都仍是原Owner待办；横杠不能替代修复和能力验收。来源空结果可作为一次真实运行结果，不能单独证明所有能力已闭环。

成熟度分别记录能力状态、维度定义/展示覆盖、实际数据覆盖/时效和来源限制；不以100%非空为统一门槛，也不把允许缺失改成100%覆盖。保留真实分子/分母、受限/缺失/失败数和影响；业务问题所必需的证据不足时，相关结论仍未知或不可用，不能因为UI完整就通过业务结果。Global/Reference三项原验收维度采用已披露范围及可解释限制，不声称全球数据齐全。

时间排序保留原始出版、事件、采集/刷新三类时间、时区与精度；按任务选择对应时间轴，同源同精度可比较。未知时间单列“日期未知”，不得补造；只有日期精度不伪造秒级先后。明确用户时间筛选时，无法确认落入范围的项单独提示，不算已覆盖。无全局硬起点不等于无范围、无节流或无限回溯；Scheduler沿现有预算、游标、水位与授权轮换持续运行。

**当前执行归属：** C1 持续完成自身闭环及所需既有 Core/runtime、Scheduler、授权绑定依赖，不暂停或切给 C6；架构 Owner 和共享文件保护不变。`2d0f8d61` 对 `acquisition_plan.py`、`adapters/scheduling/prelaunch_baseline.py` 硬编码起点的观察只作历史定位，不代表当前未提交源码或运行状态。C1 按当前源码及真实执行回执处理可选任务时间范围、Scope/授权、capture 上界与精度；保留旧 plan/receipt 及 fingerprint。依最新 PO 策略保留历史测试与失败，不新建、运行或修改模块测试求绿。通过实际产品操作核明确范围、未指定范围、未知日期、旧回执恢复、真实持久化和持续刷新；规则发布不等于运行通过。

### 当前 C1 提速顺序 — 主体批量采集、后置分析与单封面

2026-10-08 Product Owner 在 C1 原窗口的直接补充（消息
`01a11bb2-b90c-7c53-b3b8-1327cc8b54b0`）调整本轮处理顺序：根据主体大量采集相关发帖，返回后直接跑数据处理，关键词采回后分析；图片只处理一张封面。M 在当前窗口被明确要求优化、同步并回传 C1。它覆盖旧说明中与该顺序矛盾的前置词条完善或逐图处理，不扩大身份、权限、来源或费用。

1. **先按主体扩面。** 用已绑定的 Subject/BrandFocus、真实名称/别名和任务语义编译现有平台可执行查询；登记来源、市场/门店、任务时间及歧义。批量、分页和平台轮换沿原 Collector/Scheduler 的许可、预算、速率、冷却、游标与恢复执行。无需先补齐完整话题词库、热榜或 AI 分析再开始当前主体的真实采集；不能为扩大数量放宽范围校验或混入同名异地主体。
2. **每批立即进入原数据链。** 返回的允许内容按原有身份/幂等/事务规则进入 Source→Evidence→Canonical，并可供检索和下游消费；不等待六个平台或所有查询结束。一个坏来源/媒体/受限平台不能撤销其他有效结果，也不能使整批假成功；保留逐项接收/拒绝/待补状态、原文覆盖、检查原因、断点和真实接收计数。摘要或截断观察不冒充全文；只有现有正式准入通过的记录进入 Canonical。
3. **关键词后置。** 从已取得的原文和来源版本分析主题/词条，沿现有词库追加版本、关联与有效时期；旧词不删。来源语言、任务用词和检索别名仍可用于采集，但词库增长、热度测量和模型推理不是采集前置。无可用分析服务时保留待分析，不阻塞已有真实数据处理；不虚构主题、官方标签、热点或热度。
4. **只处理一张封面。** 当前批量采集每帖最多处理一张平台实际提供的封面/主图；无封面保留缺失原因。保留其他原媒体的定位、元数据、来源与版本，但不在此路径批量下载/转码其他图片、抽帧或逐图分析，也不重写已存原件。一张封面不证明全图集/全视频已看；既有创作/资料任务所需原媒体、具体用户输入和其独立验收范围保留，不能把本项成本优化误读为删除媒体能力或抹除原材料。
5. **C1 持续自闭环。** 沿自己现有 Task/Goal、Scope、授权、Core/runtime 与 Scheduler 执行并记录实际吞吐、延迟、准入数、错误原因和恢复；不另造采集器/队列、无逐帖审批或逐函数消息。采集及处理必须由产品代码持续执行，Codex 手动操作不替代。源码、规则、当前状态随合格有界批次发布；仅统计计划/Raw 数量不能宣称闭环。

### 已核读资料进入 C1 当前闭环 — 2026-10-08

下列要求适配已读本地内容/平台研究原件及现有 RC-03/04/08/13 路由，增强同一 J1/U01–U05，不新增采集器、资料库、任务卡或统一数据模型。C1 在当前完整任务内连续执行，不等待其余资料全部读完或 GPU：

1. **保留原件与实际覆盖。** 经现有 Source/Evidence/Canonical 保存原始身份、URL、版本/hash、发布/事件/capture 时间及现有精确 locator。全文、摘要、截断正文、封面、视频区间、转录和音频实际读取分别记录；元数据/标题/封面不能写成原文或全片已读。分页失败、缺图、媒体不可得等保留具体原因和可恢复位置，不能用成功的 HTTP 或总条数冲抵。
2. **去重不丢来源。** 复用当前去重/版本接口；同文转载仍保留各来源身份、时间、链接和引用关系。前缀相同或长度接近只可作相似候选，不能静默删除独有材料或认定版本等价。原件读取只证明内容取得，不自动验证其主张、代表性、商业复用或训练资格。
3. **采集事实可供研究比较。** 原文明确提供的地区/门店、适用时期、主体关系、内容角色、广告/赞助披露及指标定义，经现有 provenance/原文定位传递；未披露保持未知。KOS/KOL/KOC/UGC、付费关系或受众身份不能仅凭粉丝量/互动量推定。样本/总体、分母、对照及结论由 C3/C5 在相应研究任务中解释，C1 不凭抓到的热帖代替完整市场或因果判断。
4. **保持闭环接线。** 给既有下游真实 source/evidence/canonical refs、完整或部分覆盖状态、版本和可用动作；真实任务检索/打开原文/刷新/重开时能够回到同一来源。原文部分缺失与产品解析缺陷分开处理；不得因界面可显示“—”而跳过可修复缺陷。源变化沿现有引用传递，历史版本保留。

以上是当前执行与质量要求，不宣称所有字段或消费者已经实现。C1 将实际缺口与采用结果更新到自己已有任务/回执，M 只审查完整成果和跨边界冲突；不增加逐函数报告或重复 ACK。身份、访问政策、来源用途、速率和生产数据边界保持。
