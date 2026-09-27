# ROUND 06 — dated CTH and BMP public-source captures

## Accepted source slice

The existing SYSTEM public HTTP adapter now recognizes a bounded publisher
article container used by Swire Properties and a government article body, and
reads a visible `DD Mon YYYY` date when it agrees with other declared signals.
The previous 1,000-character excerpt limit plus ellipsis remains. This is a source extraction
improvement, not a new Collector, metric, source right or domain owner.

## Verification

- Clean `13c673960101ba75930603ee788b136555c09489` archive with only the
  adapter and focused regression copied in: 46 targeted/adjacent tests PASS.
- Shared checkout: 78 targeted/adjacent tests PASS, including local prelaunch
  and BMP scope regressions, using an external isolated test DB.
- [Nike newsroom release](https://about.nike.com/en/newsroom/releases/nikelab-running-brings-together-performance-craft-and-style-for-every-run)
  was captured in the actual local v17 product DB under the existing Nike BMP
  BrandFocus. Its source-declared publication time is
  `2026-09-09T07:00:00-07:00`.
- [Swire Properties' Taikoo Hui Guangzhou anniversary release](https://www.swireproperties.com/en/media/press-releases/2021/20210910_taikoo-hui-guangzhou-celebrates-10th-anniversary/)
  was captured under the existing Guangzhou Taikoo Hui CTH Subject. Its
  visible publication date is `2021-09-10`; this is a historical campaign
  source, not current venue performance.
- Each new record has one Raw row, one Canonical row, a distinct signed
  Evidence reference and exact domain/Subject or BrandFocus scope. Raw and
  Canonical read-back showed `data_quality_status/quality_status=ok`, score
  100, and the source publication time. The manual local import took a
  verified SQLite backup before each product-DB write.
- Latest read-only actual DB check: schema v17; 107 registry entities,
  114 Raw notes, 114 Canonical records, 114 Evidence records; 112 older
  rows remain `error`, two new rows are `ok`; `integrity_check=ok` and zero
  foreign-key violations. The operator source and exact-scope dependencies
  remain `LOCAL_ONLY / NOT_PUBLISHED` and are not accepted by this Batch.

## Product boundary

The source pages are publisher-authored statements. They establish a dated
public communication signal only; they do not establish media reach,
consumer response, marketing effects, venue sales or global coverage.
Commercial source-rights state remains `pending_review`; these captures are
internal development evidence. The actual product DB is local and is not a
GitHub artifact. Product Context still has an observed `401 AUTH_REQUIRED`
real-user path gap. Global Commercial/Brand Coverage, real user E2E, ROUND 06
and release remain unaccepted.
