# Existing registry country projection — 2026-09-28

Base: `379772ff05d041a475f670a7db173454fa347bb1`. This bounded source Batch
extends the existing Subject Registry GET; it does not accept ROUND 03 or P0.

## Real delivery card

- Real user job: find a commercial Subject or BrandFocus in a country without
  confusing headquarters, operating markets and venue location.
- Entry: `GET /api/settings/subjects?domain_id=CTH&country_iso=US&relation_type=VENUE_LOCATION`.
  Both country and relation filters require an explicit domain. Existing unfiltered
  discovery/add routes remain available; filtering never triggers acquisition.
- Real input: existing v18 entity assertions, signed source Evidence and registry.
- Result: selectable registry rows plus `country_projection`, including relation
  role, source refs, capture time and review status. `country_categories` provides
  the 13 named countries plus OTHER. OTHER is a view, not a stored country.
- Rejected/inactive memberships are not selectable. Observed count is not global
  coverage: `coverage_total=null`, `coverage_status=NOT_VERIFIED`.
- Permission: existing authenticated actor and domain read checks execute before
  either registry or relation reads; denied requests never reach either reader.
- Recovery: invalid/incomplete filters return 400; missing relation schema returns
  503 rather than empty success. Source assertions are not modified.
- User-visible E2E: `LIVE_NOT_VERIFIED`; frontend binding and the existing canonical
  local session are still being integrated. No synthetic session was used as proof.

## Verification

Clean accepted-source archive, external disposable test seed, offline tests:

`python -m pytest -o addopts='' -q tests/test_public_source_adapters.py tests/test_shared_database_entity_relations.py tests/test_subject_registry.py`

Result: **35 passed**, exit 0, no background-thread leak. The Atom/RSS negative
regression health mocks now accept source keyword arguments introduced by the
previous accepted collector change; all no-identity/no-import assertions remain.
Constitution Gate passed. No test was removed, quarantined or weakened.

Read-only invocation of the actual projection against the existing product DB
returned CTH US/VENUE_LOCATION=50, CTH CN/VENUE_LOCATION=2, BMP US/HQ=1 and
BMP CN/OPERATES_IN=1. All returned claims had verified signed Evidence; all four
views remained UNREVIEWED and total coverage unknown. This proves data consumption,
not HTTP/user acceptance or market completeness. No product DB write/migration.

## Global universe / data maturity impact

Existing country assertions now have a typed registry API consumption path.
Global Commercial Coverage=NO; Global Brand Coverage=NO; Guangzhou depth=PARTIAL;
FULL_UNIVERSE_READY=NO; ROUND 03=REWORK. Country 50+50 population, platform native
data/history, maintenance and real user jobs remain separate unmet obligations.

## Continuous frontier research / capability evolution

ADAPT the existing `intelligence_library/07_Data-Evidence-Evaluation/COUNTRY-MARKET-RELATIONSHIP-NAVIGATION-2026-09-27.md`
and current Global Universe contract: expose explicit relationship roles through
the one registry/relations owner. No new dependency, store, schema or UI authority.

## Commercial overlay impact

No rights or commercial promotion: source restrictions and unreviewed status remain.
RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO.
