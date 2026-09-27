# ROUND 06 — anonymous redirect continuity

Base: 4d8a876b9ac53fa945e7dee3dcbdb759068fc9e2.

## Bounded owner repair

SYSTEM Collector public_source.fetch_public_url owns the anonymous session.
Requests retained a redirect Set-Cookie internally; the next request then hit
the existing no-Cookie guard. Clear only the internally created cookie jar after
each response. Supplied sessions remain subject to the unchanged guard. DNS
resolution/pins, redirect revalidation, TLS identity and byte/time bounds remain.
No credential export, new auth route, dependency or source authorization change.

## Current verification

23 focused transport tests passed with exit 0 and no thread leak: real Requests
cookie extraction followed by a second synthetic redirect request with no Cookie;
caller Authorization/Cookie and synthetic netrc blocked before network; existing
private/loopback redirect cases retained. Source AST and exact staged candidate
content checked. Tests used an explicit disposable seed, not the product DB.

A real first-party Pantene Brazil probe used the existing opted-in public DoH
fallback and existing transport: https://pantene.com.br/pt-br/ redirected once to
https://pantene.com.br/pt-br, HTTP 200, 65,704 bytes, two resolution events. The
first probe without this workstation's DoH option failed closed on local DNS;
no private address was used and no hardcoded IP was added. No DB write here.
This does not claim source-field extraction, market attribution or 50+50 coverage.

## Actual product data follow-up

The accepted source-name admission path ran against actual Shenzhen MixC Luohu
with query 深圳罗湖万象城 and exact manual DATA_IMPORT/COMMIT approval. One source
7413704265102904626 explicitly names 深圳万象城 and was added to Raw, native fields
and Canonical under that Subject, signed Evidence 375. Two other source payloads
remain unassigned review candidates inside that Evidence. Overall result stays
PARTIAL_SCOPE_REVIEW_REQUIRED, not successful full refresh. The prior three
Shenzhen Bay records remain UNASSIGNED. Fresh readback: integrity OK, FK0.
Private backup and full result: data/backups and the local bounded run artifact;
no Cookie/session or production DB bytes are published.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: ingest real public and social material without false transport failures or
false entity attribution. Entry/input: explicitly approved prelaunch public
source and manual Luohu search. Path: existing Collector -> signed Evidence ->
Raw/native/Canonical for admitted source. Visible-result workflow/UI review is
NOT VERIFIED. Failure/recovery: unchanged auth/SSRF fences; preserve pending
observations; previous wrong associations stay withdrawn.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: useful transport and bounded real-data
increment; no country/Global maturity promotion. COMMERCIAL OVERLAY IMPACT:
commercial readiness remains NO. CONTINUOUS FRONTIER RESEARCH / CAPABILITY
EVOLUTION: existing Requests session behavior reproduced and corrected in the
existing owner; no new framework/architecture justified. ROUND 06 REWORK.
