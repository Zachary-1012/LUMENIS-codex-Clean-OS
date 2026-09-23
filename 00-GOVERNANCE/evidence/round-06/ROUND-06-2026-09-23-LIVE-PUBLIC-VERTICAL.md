# ROUND 06 — isolated public-source vertical probe

Status: **one technical CTH subject-scope path LIVE VERIFIED LOCALLY; ROUND 06 NOT ACCEPTED**

Observed: 2026-09-23 12:01–12:03 Asia/Shanghai
Source: current dirty local tree over `77648c3b010d7f1ec1ce516f4d15ed99e7c34378`; the collector, Evidence, Permission and reporting changes used here are not represented by that remote SHA.

## Boundary and source

`python scripts/acceptance_live_public_result.py --source-url https://www.taikoohui.com/` used only a disposable OS-temp SQLite database and artifact directory, an in-process random Evidence HMAC key, and an explicitly provisioned subject-scoped operator. It did not use XHS, a browser profile, CDP, Cookie, a resident scheduler, production collection or the production database. The test made one public HTTP read from the Guangzhou Taikoo Hui site; [Swire Properties' own property page](https://www.swireproperties.com/en/portfolio/current-developments/taikoo-hui-guangzhou/) identifies that domain as the property's website. A technically readable public page is **not** proof of commercial reuse rights, retention approval or source-policy completion.

The first run failed closed: this workstation's normal DNS returned synthetic `198.18.0.169`, which the public-source SSRF guard rejected. It recorded `PROVIDER_UNAVAILABLE`, a failed Evidence trace, zero Canonical rows and no report. `curl` returning HTTP 200 was not treated as collection success. Two independent DNS-over-HTTPS resolver responses then identified the same globally routable address for the exact host. A **process-local** `LUMENIS_PUBLIC_SOURCE_HOST_PINS` exact-host pin permitted the existing guarded transport to fetch the page with original TLS hostname validation; no permanent pin or security bypass was installed. The resolver answers had short TTLs and must not be hard-coded as durable source configuration.

## Successful second run

The second probe exited `0` with `ok=true`. Its isolated database was `C:\Users\28049\AppData\Local\Temp\lumenis-live-public-probe-jrbnr84j\isolated.sqlite3`; the report artifact was under a separate OS-temp `lumenis-live-public-probe-z6400j3e\artifacts` directory. The probe migrated its own database to v17, created the Guangzhou Taikoo Hui Subject and a least-privilege actor, and first verified that an unauthorized cross-scope collection attempt made **no network or persistence attempt**.

| Observed result | Value |
| --- | --- |
| Authorized public HTTP read | `SUCCESS`; one raw item returned and imported |
| Canonical and source records | one `notes` row and one `canonical_data` row, up from zero |
| Evidence | one recorded collector Evidence row, result `PASS`, integrity v2 `verified`, writer-authenticated HMAC |
| Permission denial | `SCOPE_UNAUTHORIZED`; no network and no persistence attempted |
| Scoped report | one `daily_reports` row; generated and reopened with identical content and lineage hashes |
| Report artifact SHA-256 | `703c8f9b2a5b1c1434c242bbbf515c10197b7f219ab09320f75a4f528a979263` |
| Production `data/monitor.db` | before/after SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, size `1,458,176`; WAL/SHM absent before/after |

The generated report only states the single verified source record and lineage; it does **not** establish footfall, sales, global coverage, market maturity, a customer result, or a commercial source license. `GLOBAL / ALL`, BMP, XHS allowlisted collection, recurring operation, retention and browser/mobile delivery remain unverified. The failed first run and both disposable databases/artifacts were retained for diagnosis, not silently discarded. This is an acceptance probe, not a production import or a release claim.

Targeted isolated regressions for public transport/adapters/lineage, scoped reporting and probe safety passed: initially `64` tests, then `83` after the transport and probe-gate fixes, exit `0`, with no background-thread leak. A third isolated live probe after those fixes exited `0` at 12:13 Asia/Shanghai: exact official source identity, one verified Evidence-linked Subject note and Canonical row, report/reopen, cross-scope denial before network, and unchanged production DB fingerprint were all checked. Its report artifact SHA-256 is `1247de7f91d004391ce20f1bdd4460085bb6b167a743780ad6cf0b5fde1eee09`. The transport now binds its connection to the validated public IP, rather than allowing a second DNS resolution at connect time; deterministic rebinding tests passed. This does not replace security review, source licensing/compliance, ongoing runtime operation or full Round 06 E2E.

## Sol gate

**PARTIAL / LOCAL_ONLY.** The one technical Source → Evidence → Canonical → scoped Report → reopen path is real in isolation. ROUND 06 cannot PASS until its source diff is integrated coherently, compliance and live operation are checked per Source, wider Subject/BrandFocus coverage is proven, and the full round's user-visible and failure/recovery gates pass. `COMMERCIAL_READY=NO`.
