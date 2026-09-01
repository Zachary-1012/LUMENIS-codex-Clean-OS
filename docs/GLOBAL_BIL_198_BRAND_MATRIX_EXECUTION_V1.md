# Z-Brand-Core｜Global BIL 198 Brand Matrix Execution v1

## Objective

Execute the first real inventory pass against the existing ZBMP local brand dataset and prepare it for Global BIL benchmarking.

## Authoritative Entity Rule

`brand_directory.json` remains the authoritative source for the existing 198 Taikoo Hui brand entities. Global benchmark brands are separate benchmark entities and must not overwrite or duplicate the local brand master.

## Capability Matrix

Each brand is evaluated across 17 domains:

1. Entity
2. Knowledge
3. Social Voice
4. UGC
5. Consumer Voice
6. Creator
7. Product
8. Campaign
9. Geography / Market
10. Store / Channel
11. Community
12. Competitor
13. Brand Health
14. Business Momentum
15. Lifecycle
16. AI Discovery / GEO
17. Evidence

Status vocabulary:

- `EXISTS` — repository/runtime asset or validated evidence exists
- `PARTIAL` — some relevant capability/data exists but coverage is incomplete
- `MISSING` — capability is not currently represented
- `N/A` — capability does not apply to this entity/use case
- `CONFLICTED` — competing definitions or sources require resolution
- `UNKNOWN` — not yet researched; never treat as missing

## Research Order

### Batch 1 — Identity and owned assets

Entity / Knowledge / Social / UGC / Consumer / Creator / Product

### Batch 2 — Market and activation

Campaign / Geography / Store-Channel / Community / Competitor

### Batch 3 — Outcome and learning

Brand Health / Business Momentum / Lifecycle / AI Discovery / Evidence

## Evidence Rule

Every `EXISTS` or `PARTIAL` claim used in a production-facing mapping must point to an inspectable repository asset or dated external evidence. Unknown data must remain `UNKNOWN`.

Dynamic metrics such as followers, UGC volume, social mentions, AI visibility and store status require `observed_at` / capture timestamps.

## Benchmark Rule

Benchmark selection is mechanism-based, not popularity-based. A benchmark may be S/A/B/C, but benchmark rank must never be confused with brand importance, revenue, follower count, or social volume.

## Scoring

Do not calculate a single brand score from raw capability coverage.

Maintain separate dimensions:

- `data_coverage_score`
- `evidence_quality_score`
- `benchmark_relevance_score`
- `brand_importance_score`
- `mechanism_fit_score`
- `transferability_score`

## Required Outputs

1. `brand_inventory_snapshot`
2. `brand_capability_matrix`
3. `brand_evidence_index`
4. `benchmark_mapping`
5. `gap_priority`
6. `staging_import_manifest`

## Gap Priority

Priority should combine:

`strategic_value × capability_gap × evidence_feasibility × reuse_value`

with safeguards against turning low-data brands into low-importance brands.

## Production Guardrails

- No production migration in this pass.
- No modification of existing Brand Master semantics.
- No fabricated follower, UGC, sales, store, purchase-intent or AI-visibility values.
- No silent replacement of existing ZBMP logic.
- No bypass of platform controls or terms.
- Staging first; shadow validation before runtime integration.

## Research Context — 2026

Current industry research reinforces separate layers for social/creator, commerce, consumer voice and AI discovery. Creator content is increasingly used across paid media and conversion, while AI answer engines increasingly influence product discovery. Semrush reports a 2026 study based on 126 million AI search prompts; Kantar reports that AI-driven experiences are reshaping brand discovery and loyalty; NIQ describes AI as changing product discovery and the purchase journey. These are external benchmark signals, not direct measurements of the ZBMP brands.

## Definition of Done

This phase is complete when every existing brand has an explicit status for all 17 domains, all non-UNKNOWN positive claims are evidence-backed, benchmark relationships are explicit, and a staging import can be generated without modifying production behavior.
