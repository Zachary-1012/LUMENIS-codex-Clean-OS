# Singapore BMP market-activity source decision — 2026-09-27

The [Overture Maps Places release `2026-09-23.1`](https://docs.overturemaps.org/guides/places/)
is a versioned, open Places dataset with [source-specific licensing and attribution](https://docs.overturemaps.org/attribution/).
Its `brand` and Singapore address fields can suggest where an existing BMP
BrandFocus may have physical market activity. It does not establish brand
origin, headquarters, legal jurisdiction, direct store ownership, campaign
activity, sales, or customer response. Overture itself warns that confidence
does not resolve duplicates and incomplete properties.

An exact normalized-name comparison against the current 101 BMP Registry rows
found 30 BrandFocus names with at least one Singapore place at existence
confidence `>=0.95`. The reproducible bounded queue is
`scripts/data_candidates/overture_sg_bmp_registry_market_candidates_20260927.jsonl`;
its manifest records the release and SHA-256. All 30 are `REVIEW_PENDING`,
with zero accepted `MARKET_ACTIVITY` relations and no product DB write.

Decision: **ADAPT as candidate discovery** for the existing BMP Registry →
SYSTEM Collector → Evidence → Canonical → Entity Relation owner chain. Review
the place, brand identity, country and source attribution before assertion.
Store-level evidence may support `MARKET_ACTIVITY`; do not silently upgrade it
to `OPERATES_IN` or count it toward the Singapore 50-brand acceptance floor.
Versioned monthly releases can later support incremental refresh through the
existing scheduler only after an exact source approval and recovery path.
