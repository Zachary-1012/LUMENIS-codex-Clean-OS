# Round 06 — Overture Places Parquet candidate reader (2026-09-27)

Status: `TESTED CANDIDATE READER / ROUND 06 REWORK`. The SYSTEM Collector
adapter produces review candidates only and does not write the product DB.

## Source and library

- Overture Places [attribution and source licenses](https://docs.overturemaps.org/attribution/),
  accessed 2026-09-27. Places combines upstream sources with differing
  attribution requirements. A license field in a source row is provenance,
  not automatic approval for a specific LUMENIS publication or refresh plan.
- DuckDB 1.5.5 is pinned in `requirements.txt` and registered as an MIT-licensed
  local Parquet reader. It uses an in-memory connection, not a second business DB.
  See [versioned license](https://github.com/duckdb/duckdb/blob/v1.5.5/LICENSE).

## Verification

- Seven scoped parser/reader tests passed with DuckDB 1.5.5 isolated under
  the workstation temporary directory.
- The real local Singapore Parquet snapshot was read without DB writes:
  SHA-256 `C920AB993F3C57891ACF0819147E055ED6F012C4FCC9587FDAB9D2A893BE2404`,
  31,258,159 bytes, 162,217 input rows. Parser output: 13,599 candidate
  mall/brand-place rows, 24,319 out-of-country rows, 124,299 other rows.
  All 13,599 candidate rows carried nonempty upstream source records with
  recorded license values. These counts are *not* 13,599 reviewed entities.
- Stable source identity, country filtering, explicit unknown fields,
  deterministic deduplication, and rejection of remote/glob paths are tested.

## Remaining gate

The current 50 Singapore commercial and 30 brand/market review leads remain
unaccepted until exact entity matching, source rights/attribution review,
authorized Source registration, Collector Raw, signed Evidence, Canonical
binding, and relation review occur. No operating status is inferred when the
source omits it. No Global coverage or real user E2E status changes here.

Global Commercial Coverage: `NO / NOT VERIFIED`. Global Brand Coverage:
`NO / NOT VERIFIED`. Guangzhou reference: `PARTIAL`. Full Universe, RELEASED,
OPERATING and COMMERCIAL_READY: `NO`.
