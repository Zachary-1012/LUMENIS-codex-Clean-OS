# Z-Brand-Core｜Global BIL Next Execution Plan v1

> 2026-09-01
> Scope: Global Brand Intelligence / ZBMP
> Status: Execution plan; staging-first; no production cutover

## Objective

Turn Global BIL from a research protocol into a validated intelligence layer that reuses existing ZBMP assets and can later support global-to-local brand analysis.

## Workstreams

### A. Global Case & Mechanism Research

Continuously research representative brands and extract reusable mechanisms rather than writing static brand profiles.

Coverage:
- luxury / designer
- outdoor / sports
- beauty
- DTC / digital-native
- retail
- community-led
- creator-led
- product-led
- campaign-led
- heritage revival / comeback
- decline / failure
- market expansion
- cross-cultural localization
- social-to-commerce
- AI discovery / GEO
- reputation / crisis

Every case must distinguish FACT, OBSERVATION, INTERPRETATION, HYPOTHESIS and RECOMMENDATION.

### B. Existing ZBMP Brand Inventory

Use existing ZBMP brand assets as the authoritative starting point. Do not create a parallel brand master.

First-pass sources:
- `brand_directory.json`
- existing brand knowledge/index assets
- case library
- intelligence/report/stat modules

Output:
`brand_id × capability coverage matrix`

### C. Capability Mapping

For every existing brand, map:

- Entity
- Knowledge
- Social Voice
- UGC
- Consumer Voice
- Creator
- Product
- Campaign
- Market/Geography
- Store/Channel
- Community
- Competitor
- Brand Health
- Business Momentum
- Lifecycle
- AI Discovery/GEO
- Evidence

Use statuses:
`EXISTS / PARTIAL / MISSING / NOT_APPLICABLE / CONFLICTED / UNKNOWN`

### D. Benchmark Selection

Benchmark priority must not be based only on followers or social volume.

Score dimensions:
- strategic relevance
- archetype coverage
- market diversity
- mechanism diversity
- lifecycle value
- evidence quality
- data availability
- transferability

Classify:
`S / A / B / C`

### E. Staging Data

Research records enter staging only after normalization and entity resolution.

Required evidence metadata:
- source
- observed_at
- published_at when available
- market
- platform
- evidence_type
- quality_status
- confidence
- method_version

Dynamic metrics must retain capture time.

### F. Learning Layer

Convert validated cases into reusable mechanisms:

Case → Evidence → Mechanism → Conditions → Outcome → Transferability → Hypothesis → Observed Result → Feedback → Pattern Revision

A learned pattern must remain traceable to evidence.

### G. AI Discovery / GEO

Treat AI visibility as a separate discovery layer from SEO and Social.

Track where evidence permits:
- query
- market
- language
- engine/model
- brand mention
- recommendation
- position
- citation
- citation source
- competitor co-mentions
- framing
- observation date

## Architecture Guardrails

1. Reuse existing ZBMP Brand Entity; no duplicate brand master.
2. Research/staging data must not overwrite CTH-POMS production facts.
3. Do not introduce production migrations until staging validation passes.
4. Do not fabricate UGC, follower, store, sales or purchase-intent values.
5. Inference must be explicitly labeled as inference.
6. Platform controls and terms must be respected; no bypass scraping.
7. Existing production modules remain intact unless a compatibility-tested adapter is approved.
8. UI/API work follows data-contract validation, not the reverse.

## Acceptance Gates

### Gate 1 — Research integrity
- representative global cases covered
- mechanisms extracted
- evidence and dates retained
- facts separated from inference

### Gate 2 — Inventory integrity
- existing ZBMP brands enumerated
- duplicate entities resolved
- capability coverage mapped

### Gate 3 — Staging integrity
- schema loads cleanly
- foreign keys/entity references validate
- duplicate evidence is idempotent
- rollback path exists

### Gate 4 — Shadow integrity
- BIL outputs run beside current ZBMP
- no production behavior changes
- metric discrepancies are explainable

### Gate 5 — Production readiness
- regression suite passes
- migration reviewed
- observability present
- rollback tested
- only then consider production adapter/cutover

## Immediate Next Actions

1. Complete global benchmark research set.
2. Extract structured case mechanisms.
3. Enumerate the real ZBMP brand inventory.
4. Produce the capability matrix.
5. Select S/A benchmark brands.
6. Populate only evidence-backed staging records.
7. Run entity-resolution and metric validation.
8. Prepare shadow adapter specification.

## Definition of Done for this phase

A reviewer can answer, from repository artifacts alone:

- Which brands are in ZBMP?
- What BIL capabilities already exist for each brand?
- What is genuinely missing?
- Which global cases teach each missing capability?
- What evidence supports each case/mechanism?
- Which data is safe for staging?
- What remains blocked from production and why?
