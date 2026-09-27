# ROUND 06 — public-source resolution and provenance Batch

## Scope and source

The existing SYSTEM Collector public-source transport now permits an explicit
`LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK=1` when workstation DNS fails or returns
only non-global addresses. It queries the fixed Google DNS-over-HTTPS JSON
endpoint over verified HTTPS, accepts only a validated CNAME/A chain with
globally routable addresses, pins the chosen address to the original HTTPS
hostname, and revalidates every redirect. Literal IP targets and mixed
public/private DNS answers cannot use the fallback. The response carries a
bounded requested URL, redirect chain, and resolution trace for the existing
Evidence owner. The fallback is off by default and introduces no Cookie,
platform session, or automatic collection.

The source-access status is `public_read_only`; the separate commercial license
state is `pending_review`. This source Batch does not grant commercial use or
change the product's Source/Evidence/Permission owner.

## Verification on the local candidate

- `tests/test_public_source_transport.py` and five adjacent Collector,
  exact-scope, and Permission suites: 130 tests passed on the current working
  snapshot, with no background-thread leak.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: PASS.
- The bounded transport fetched live HTTPS pages for Guangzhou Taikoo Hui,
  Shenzhen MixC context, Nike, and Le Labo with HTTP 200 and pinned public
  addresses. One fresh disposable-DB Guangzhou run produced a
  writer-authenticated Evidence record, VERIFIED Canonical row, and persisted,
  reopened scoped report. The protected product DB fingerprint was unchanged.
- An official Luohu government page failed strict TLS validation
  (`BAD_ECPOINT`); certificate verification was not disabled. A publicly
  accessible operator page was separately identified, but is not accepted
  as a replacement for a complete CTH business corpus here.

## Acceptance boundary

`TESTED` SYSTEM Collector transport only. The protected product database still
has no four-entity baseline rows at this checkpoint. A real Owner session,
exact Permission, product-data write, Global/Focus user result, mature global
inventory, and real-user E2E remain unverified. ROUND 06 remains `REWORK`;
Global Commercial and Global Brand Coverage remain `NO / NOT VERIFIED`, and
`LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.
