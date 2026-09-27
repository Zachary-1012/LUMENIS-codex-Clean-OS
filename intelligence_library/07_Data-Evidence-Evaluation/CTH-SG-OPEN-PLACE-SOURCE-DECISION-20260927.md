# Singapore commercial-venue source decision — 2026-09-27

Purpose: find reusable candidate sources for the existing SYSTEM Collector →
Evidence → Shared Database CTH Subject chain. This research is not Product Truth,
an approved inclusion inventory, or Singapore CTH coverage acceptance.

| Source | Current finding | Decision |
| --- | --- | --- |
| [Overture Maps Places](https://docs.overturemaps.org/guides/places/) and [attribution](https://docs.overturemaps.org/attribution/) | Release `2026-09-23.1` is open, versioned, with source-level attribution and permissive data licences for the Places theme. Its own documentation warns about duplicates and quality. A bounded `--no-stac` Singapore extract contained 162,217 place rows; 631 were tagged `shopping_mall`, 219 of those had confidence ≥0.95, and 200 also had a website. Spot checks still found wrong category and website assignments. | **ADAPT for candidate discovery only.** A confidence score alone cannot register or verify a CTH Subject. Preserve release, contributing source, licence/attribution and row provenance if an existing import owner later uses it. |
| [Singapore mall-data on GitHub](https://github.com/curioputterings/singapore-mall-data/tree/4845a413545993bd0b807ba2a46535f63cc27fd1) | Commit `4845a413` carries CC BY 4.0. Direct readback of its `malls.json` found 87 rows, while its README table says 75 and coverage prose says 86; the stated shopping snapshot is 2026-05-27. Its compilation tooling is private and source rights are not transferred by the dataset licence. | **ADAPT for cross-check and operator-source discovery only.** Do not silently copy tenant records or treat its counts as a current baseline denominator. |
| [CapitaLand mall listings](https://www.capitaland.com/en/lease/malls.html) and [site terms](https://www.capitaland.com/en/legal-notices/terms-and-conditions.html) | The public mall directory names Singapore, China and Malaysia properties, but the current terms prohibit automated access/processes to the website. One bounded existing `PublicHttpAdapter` preflight of Funan returned content; this does not authorize scheduled crawling. | **REJECT for automatic maintenance** under current terms. Retain only as a manual research lead until an authorized route is established. |
| [Singapore URA mall/promenade plan](https://data.gov.sg/datasets/d_6fc19e9c3908942a7592d20a9a878595/view) | Government Open Data Licence permits personal/commercial use, but this planning geography dataset is not a current list of operating named malls. | **DEFER as an entity registry source.** It may provide geographic context through an existing owner after exact feature semantics are checked. |

Bounded cross-source check on the pinned files: 54 Overture rows marked
`shopping_mall` with confidence at least 0.95 matched an exact normalized name
in the 87-row GitHub list. Those rows represented **53 distinct names**, all
54 had a website, and only **43** had an exactly matching postal code. One
name appeared twice. This is a candidate intersection, not 53 verified current
commercial Subjects or an approved source-rights decision. Exact name and
postcode matches still need identity, operator and operating-status review
before any Registry/Evidence/Canonical acceptance.

Next data Batch: choose a rights-compatible candidate source, verify stable venue
identity and current operating status with a second independent source where
needed, then ingest through the existing CTH registry/Permission/Collector/
Evidence/Canonical path. A source candidate or secondary directory count is
never counted as a verified Singapore CTH entity. Target policy remains the
Product Owner's 14 country categories with at least 50 commercial entities
and 50 brands per category; `OTHER` is a display bucket, not a country code.

Bounded 50-venue review queue: `scripts/data_candidates/overture_sg_cth_50_review_queue_20260927.jsonl`
selects 43 distinct exact name-and-postcode cross-source matches, plus seven
distinct venues with an operator or venue source discovered for manual address
review. All 50 remain `REVIEW_PENDING`, with zero accepted Subjects and no
product DB write. The manifest pins the source versions and JSONL fingerprint.
In particular, Overture's Aperia Mall point used the office tower postcode
`339510`, while [CapitaLand's property factsheet](https://www.capitaland.com/content/dam/capitaland-media-library/businesspark-industrial-logistics/singapore/singapore/aperia/Aperia-Factsheet.pdf)
identifies the mall at `339511`; it was excluded from this queue. This is a
concrete reason to review venue identity and location rather than promote
high-confidence map points automatically. Operator websites are research
references here, not approved automatic Collector sources.
