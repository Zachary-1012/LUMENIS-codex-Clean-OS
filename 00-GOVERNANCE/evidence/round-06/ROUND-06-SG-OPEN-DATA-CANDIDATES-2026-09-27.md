# ROUND 06 — Singapore open-data candidate queues (2026-09-27)

Status: `RESEARCH / REVIEW_PENDING`. This is source discovery, not accepted
Global coverage, product DB data, a collected run, or a real user result.

- Pinned [Overture Places release `2026-09-23.1`](https://docs.overturemaps.org/guides/places/), with [per-source licensing and attribution](https://docs.overturemaps.org/attribution/), was inspected in a bounded Singapore extract. The upstream warns that high existence confidence does not remove duplicates or incomplete/wrong properties.
- A pinned [CC BY 4.0 mall directory commit `4845a413`](https://github.com/curioputterings/singapore-mall-data/tree/4845a413545993bd0b807ba2a46535f63cc27fd1) was used only to cross-check candidate identity; its row counts are internally inconsistent and it is not a current operating-status authority.
- The CTH queue has 50 distinct venue candidates: 43 exact name/postcode cross-source matches and seven operator-source review leads. Its manifest SHA-256 is `5fe7104fc8955137bd76e79fdedd88be386c7b05b1ccd1935d30e7cd2f9f9c70`. The incorrect Aperia mall postcode in Overture was identified and excluded; no venue is accepted by this queue.
- The BMP queue matches 30 existing BrandFocus names to Singapore Overture brand/place records at confidence ≥0.95. Its manifest SHA-256 is `ed26b6f86969f2f2c357e77c70da453a086d3dfba70c1be513d9ec96be15929a`. These are possible `MARKET_ACTIVITY` leads, not HQ/origin/legal/`OPERATES_IN` claims. No country relation is accepted by this queue.
- Both JSONL fingerprints and `candidate_only` flags were verified on the final local snapshot; 50 and 30 rows respectively. No production DB write was made for these queues.

Exact research and next owner mapping are in the CTH and BMP Singapore source
decisions under `intelligence_library/07_Data-Evidence-Evaluation/`. Import,
Evidence, Canonical and exact relations remain a later Round 06 owner Batch.
Current product DB facts remain the separately recorded local v18 totals;
Global Commercial/Brand Coverage is `NO / NOT VERIFIED`, Guangzhou reference
`PARTIAL`, and ROUND 06 `REWORK`.
