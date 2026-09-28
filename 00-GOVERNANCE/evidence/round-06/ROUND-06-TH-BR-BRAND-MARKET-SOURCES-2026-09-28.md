# ROUND 06 — Brazil and Thailand brand source/market assertions

Date: 2026-09-28. Product database: `data/monitor.db` (private, excluded from Git).
Owner chain: existing Registry → public HTTP Collector → Raw → signed Evidence →
Canonical → BMP BrandFocus → v18 Entity Relations. Exact local source candidates
were first applied twice to a disposable SQLite clone. Attack's extracted official
body lacked its brand anchor, so it remains `REVIEW_REQUIRED` and was not applied.

The three verified candidates were admitted to the actual product database with
an integrity-checked SQLite backup at
`data/backups/lumenis-th-br-four-20260928T052046Z/monitor.db`:

| Brand | Exact BrandFocus | Signed Evidence | Source result |
| --- | --- | ---: | --- |
| Downy | `BRAND-8925d818c392cbf600b5dbf3` | 404 | Brazil official source, publication time unknown |
| Ready | `BRAND-39287b070633837b9e77b7c0` | 405 | Thailand official dated release, 2019-03-28 |
| Sponsor | `BRAND-f7490b09183e2ac3f9832669` | 406 | Thailand official product page, publication time unknown |

Each exact source was collected twice: first pass imported one row; second pass
updated the same identity. Each has one Raw, one Canonical, one native public HTTP
record, `VERIFIED` scope and writer-authenticated Evidence. Actual product DB
reopened with integrity `ok`, FK violations 0; Registry count became 167.

The relation owner then received a separate disposable-clone proof and an actual
DB apply after a second verified backup at
`data/backups/lumenis-bmp-relations-20260928T052925Z/monitor.db`.
Three exact, deduplicated `MARKET_ACTIVITY` assertions were reopened: Downy–BR
`275`, Ready–TH `277`, Sponsor–TH `279`. Each references the exact source note and
signed Evidence, and each remains `UNREVIEWED`. Relation count became 274;
integrity `ok`, FK violations 0. No AUTO collection plan, social-platform fact,
commercial data reuse right, HQ/origin/operations claim or approval of the
assertions is inferred.

This is a bounded public-source data increment. The 14 country groups × at least
50 commercial and 50 brand entities, platform-native social/consumer dimensions,
historical series, user-result paths and complete Global coverage remain open.
`ROUND 06=REWORK`, `FULL_UNIVERSE_READY=NO`, `RELEASED=NO`,
`OPERATING=NO`, `COMMERCIAL_READY=NO`.
