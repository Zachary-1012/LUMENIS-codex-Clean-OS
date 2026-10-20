# 寰意 / OEVIRA — Codex Takeover CURRENT

Current display identity (2026-10-18): **寰意 / OEVIRA**. The existing [canonical naming authority](CANONICAL-NAMING-AND-TWIN-SYNC.md) governs this rename. Technical identifiers, package names, environment variables, commands and source paths retain their compatibility spelling; dated records below preserve their original names and evidence.

Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**

## 2026-10-20 Issue #17 FIX-045 / FIX-046 — preserve EMV inputs and reject invalid route CPM

The existing `emv.py` keeps source/aggregate values truthful; `ic_routes.py` applies default CPM only when the parameter is absent and rejects explicit nonnumeric, negative, nonfinite or overflow inputs before DB/EMV reads. Platform grouping now retains no-data groups and counts unavailable notes alongside amount-bearing notes, with per-platform status and coverage. Focused runs passed **34 tests** across `tests/test_ic_emv_route_validation.py` (9), `tests/test_ic_contracts_p1.py::TestIC021EMV` (15), and `tests/test_p1_gap_closure.py -k emv_platform` (10). The broader `tests/test_ic_contracts_p1.py tests/test_p1_gap_closure.py` run had **4 failures**, and the exact same four test IDs and outcomes reproduced on clean main SHA `3f6d67785752b465b5b022847cbbe75a55e1eb47`: three API smoke imports are blocked because migration refuses to overwrite the pre-existing `/tmp/backups/before_migration_v0_to_v21.db`, and the unrelated Track B test expects provider status `LEGACY` while receiving `DISABLED`. The broader result remains recorded, not represented as a passing regression. Changed-source compilation and `git diff --check` passed. Tests did not access production data or call an external service.

FIX-045/046 follow-up: `/api/ic/emv` also rejects a malformed or non-finite
`emv_total_yuan` from the existing calculation result with HTTP 422, while
preserving finite zero and `None` result semantics. The route regression suite
adds an injected non-finite result case; the targeted route and EMV gap-closure
suite passed. Changed-source compilation, governance machine contract, AI-native
constitution and `git diff --check` passed. The shared writer `database.insert_note` now records metric observation
provenance in the additive `notes.metrics_observed_at` column (registered in
`business_schema` note migrations) only when the caller passes an explicit
`_lumenis_metric_observation_complete=True` signal (successful detail read in
`app.py`; fully present counters in `multi_platform_import`) and all four
canonical metrics are non-null; `metric_snapshots` trend
semantics are unchanged (no snapshot on insert). `/api/ic/emv` and the
reporting engine publish an all-zero EMV only with that column
(neither a generic `detail_fetched_at` nor a historical metric snapshot is
provenance); any uncertified overwrite of a canonical metric clears it, and
the live collector (`live_engine.persist_live`) certifies only when the source
returned all four counters before normalization; otherwise the amount is
`NOT_AVAILABLE`. Legacy databases without the column keep the previous
behaviour. A row is classified complete (`OK`) only with that current
provenance: without it an all-zero row is `NOT_AVAILABLE` and a row with
positive counters is `PARTIAL` (`metric_observation_provenance` missing), in
both `aggregate_emv` and `aggregate_emv_by_platform`. The live collector
certifies only finite non-negative numeric counters or parseable counter text
(placeholders such as `N/A`/`-` do not certify). `/api/ic/emv` also validates `limit` (integer 1-500), paired ISO
`start`/`end` (start <= end) before any database read (400 `INVALID_INPUT`),
reports a capped read as `truncated`/`source_read_complete=false` (an `OK`
result becomes `PARTIAL`), and returns 503 `EMV_SOURCE_UNAVAILABLE` without
internal error text when the source read fails. Platform aggregation reports aggregate-only overflow in
`invalid_inputs` and keeps `invalid_count` to invalid notes.

## 2026-10-20 Issue #17 FIX-041–043 — KOS scope and completeness

`kos_execution.py` now filters execution records by the existing scoped-v1,
actor and BrandFocus identity, while exact-context payload matches remain
visible for integrity checks if denormalized index columns drift; malformed
in-scope bindings fail rather than leaking or being silently skipped (FIX-041).
`kos_routes.py` preserves incomplete-coverage failure and returns existing
coverage, truncation, rejected-row and classification-integrity metadata on
author details (FIX-042). `kos_engine.py` handles low-interaction diagnostics
without formatting errors and treats invalid/non-finite evidence as unknown
(FIX-043); its production caller remains unverified and is still OPEN.

Offline regression command:
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -vv tests/test_kos_scoped_execution.py tests/test_kos_scoped_profile_parity.py tests/test_kos_engine_classify_kol_tier.py`
— **23 passed**, with no background-thread leak. Changed-file `py_compile`,
`git diff --check HEAD^ HEAD`, governance machine contract and AI-native
constitution passed. Tests use isolated fixtures; no production database,
live source, model call or external effect was used. The existing KOS state
contract has no separate cancellation state, so none was added; runtime and
user acceptance remain NOT_VERIFIED.

Review follow-up: signed current-context payload matches now remain candidates
even if denormalized actor, target brand or version columns are corrupted;
`_scoped_record` compares those columns back to the authoritative request and
context. Regression cases cover each corrupted column. The same offline focused
modules now report **26 passed in 1.80s**; `py_compile` and `git diff --check`
pass. FIX-043 production caller verification remains OPEN.
## 2026-10-20 Issue #17 FIX-036 / FIX-037 — report only observed collection health

The existing `system_health_api.py` no longer infers current scheduler/login state, historical schedule slots or adaptive health percentages from notes or defaults. `today_runs` now reads only task-start records marked as observed in the existing collector stats file; legacy or unverified totals remain unknown. Per-keyword `collection_logs` are exposed as `today_keyword_observations` and keyword failure/unknown observations, never added to task runs. Task-level failure totals stay unknown because the existing task-start ledger has no terminal outcome record. `tests/test_hk_only_collection_policy.py` passed **38 tests**, including one task with 20 keyword observations. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. No real login probe, collection or production database was used.
Keyword observation outcomes now use the existing canonical `CollectionStatus` values plus documented legacy status values: failure, degraded (verification/risk/cooldown), successful/no-new-data, and unrecognized states are reported separately. Adaptive status reads `metrics.recent_success_rate` and `current_params.request_delay` from the persisted engine schema; a default 100% without an observation timestamp remains unknown. The focused health suite now passes **40 tests**, including canonical status classification and the persisted nested adaptive schema.

Login state: health projects `xhs_cookie_bridge._current_session_state()`, which is `real_session_valid` only for the same account within a 30-minute TTL and only when `record_real_session_verification(..., authenticated_readback=True)` was called from an authenticated platform readback. Preflight no longer caches a verdict: browser (CDP) reachability plus a cookie-file user ID yields `browser_connected`, never `real_session_valid`. No production caller performs an authenticated readback yet, so login stays `NOT_VERIFIED` (UNKNOWN in health) and that caller remains **OPEN**; health never probes on poll. The verdict is in-memory and is lost on restart, which also yields `NOT_VERIFIED`.

FIX-036/037 rollover follow-up: a prior-day task ledger retains `OBSERVED_TASK_STARTS` only if its stored provenance already carried that marker; an unverified legacy ledger remains `UNKNOWN` across date rollover. The parameterized midnight regression verifies both persisted marker outcomes while confirming that the previous actual run still enforces cooldown. The offline `tests/test_hk_only_collection_policy.py` module passed; changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. No login probe, collection or production database was used.

FIX-037 provenance follow-up: `record_run()` keeps the history `UNKNOWN` when it appends a real start to a same-day ledger that already contains unverified legacy counts, so observed starts cannot retroactively certify estimates. A clean empty ledger still becomes `OBSERVED_TASK_STARTS` on its first recorded start. The regression covers the mixed legacy-plus-new-start case in the same offline health-policy module; no login probe, collection or production database was used.

Review follow-up for Issue #17 findings 4321861771 and 4321861781: the summary
health endpoint now uses the same validated `OBSERVED_TASK_STARTS` task ledger
as the detailed endpoint. Unmarked, unknown, malformed or unavailable history
remains `null` and keeps collector health at warning; only observed task-start
timestamps produce a count. `recent_success_rate` is returned only when its
persisted observation timestamp is valid and within the health API's existing
24-hour observation window; stale or future observations remain unknown. The
offline `tests/test_hk_only_collection_policy.py` module passed **49 tests**;
changed-source compilation, governance machine contract, AI-native constitution,
takeover governance and `git diff --check` passed. Temporary stats files and
isolated route fixtures only. The authenticated-readback login caller
remains OPEN; no live probe, collection or production DB was used.
## 2026-10-20 Issue #17 FIX-001–003 — BMP scope and source research erratum

FIX-001 updates the existing [BMP README](../lumenis/bmp/README.md) to match
the current single-product, two-domain architecture and existing shared business
truth; it does not claim implementation acceptance. FIX-002/FIX-003 preserve the
2026-10-13 research report and correct its link pointers, URL/availability column
meaning, 145/227 arithmetic, and unreconciled 445-versus-499 subject-detail count
in a dated [same-directory erratum](evidence/round-06/ERRATUM-GLOBAL-DATA-SOURCE-RESEARCH-20261013-20261020.md).
Unpublished source-classification files, live availability, product bindings and
production coverage remain NOT VERIFIED. This documentation correction is not a
new dispatch source or a completion claim.
## 2026-10-20 Issue #17 FIX-034 — redact credential-shaped diagnostics

The existing `data_boundary.py` diagnostics sanitizer redacts prefixed cookie fields and credential-valued mapping keys while preserving metadata such as `token_count`, `token_budget`, `authorization_status` and `secret_scan_result`. The focused offline command `pytest -q tests/test_runtime_preflight.py -k 'sanitize or credential_path_classification'` passed **28 tests**. The full PR module run produced **33 passed, 2 failed** (`test_tracked_credentials_current_repo`, `test_current_repo_preflight_has_no_blocker`); both failures also reproduce on exact main SHA `3f6d67785752b465b5b022847cbbe75a55e1eb47`. Full main has those two failures plus an attestation test that still writes to the repository path; this PR isolates that output under `tmp_path`. Changed-source compilation and `git diff --check` passed. Tests use synthetic values only; no real credentials were read.

Review follow-up: the text sanitizer now also redacts camelCase cookie labels (`sessionCookie=`, `xhsCookie:`), and the mapping sanitizer redacts credential keys followed by value/container descriptors (`cookie_header`, `authorization_header`) while metadata such as `token_count` and `authorization_status` stays visible. Superseding full-module result for this head: `python3 -m pytest tests/test_runtime_preflight.py` collected **42 cases: 40 passed, 2 failed** (after the second follow-up, which also redacts lowercase separatorless cookie labels such as `sessioncookie=` and separator-free credential keys such as `apikey`/`accesstoken`/`APIKEY`, while `tokencount` and `cookie_count` stay visible) (`test_tracked_credentials_current_repo`, `test_current_repo_preflight_has_no_blocker`). On main `2d41547e` the same module produced 25 passed, 3 failed, including both of those environment-dependent failures. The earlier 35-case count above described an older head.
## 2026-10-20 Issue #17 FIX-024 — partial note and analysis upsert truth

`database.py::insert_note` now preserves stored note/source/analysis values when
a partial update omits them, distinguishes an explicit `null` from absence, and
keeps scores paired with unchanged sentiment/risk labels, and clears an omitted
risk score when its label changes. Blank quality status with a synthesized zero
score remains absent, while explicit null still clears nullable state. Negative
metric sentinels preserve prior measurements; incomplete observations do not
replace known counts, and partial payloads do not recompute classifications from
missing inputs. Unknown labels continue to clear their derived scores. Regressions are in
`tests/test_database_insert_note_transaction.py`. Exact-head offline command:
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_database_insert_note_transaction.py` — **19 passed** at the initial head (historical). After the review fixes (main merged, plus classification/sentiment/quality-score regressions), `python -m pytest tests/test_database_insert_note_transaction.py` — **22 passed** (2026-10-20 rerun). Second review follow-up: a score-only quality patch on an existing note now leaves the stored status/score pair unchanged (no `error`/`100` pairs), and the classifier receives the same `is_official` value the row stores; the same module now passes **24 tests**.
`python -m py_compile database.py tests/test_database_insert_note_transaction.py` and
`git diff --check` passed. The first isolated run lacked cached `beautifulsoup4`;
the rerun above used the local cache. This is a scoped SQLite regression result,
not production database or end-to-end product acceptance.
## 2026-10-20 Issue #17 FIX-048 — use the existing Ocean Engine request signature

The existing `ad_intelligence/platforms/ocean_engine.py` read-only balance and advertiser-info methods now call `_api_request` using its declared endpoint-first signature, preserving the existing missing-credentials blocked result. Advertiser info validates the configured ID as an integer and serializes it as the provider's JSON `advertiser_ids` query array (for example, `[12345]`), without injecting the unrelated singular parameter. `tests/test_ad_platform_collectors.py` passed **18 tests**, including a real Requests URL-preparation path with a fake transport and synthetic credentials plus rejection of a non-integer ID before request dispatch. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. No live API or account was used; provider acceptance remains unverified.

## 2026-10-20 Issue #17 FIX-032 / FIX-033 — preserve platform catalog availability

The existing `data_center_api.py` query/catalog path now distinguishes unavailable or unknown platform source state from a real empty result, preserving source availability semantics for the existing caller. `tests/test_platform_catalog_schema.py` passed **69 tests**. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. No production source, database or external effect was used.

The review follow-up also converts ISO date bounds to Unix seconds for numeric
publication columns and treats empty, malformed, or wholly uncountable platform
catalog entries as unavailable. Supported tables may still show their measured
counts, while an incomplete catalog total remains null; a real successful count
of zero remains zero. The offline command
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_platform_catalog_schema.py`
passed with no daemon-thread leak. Changed-source compilation, the governance
machine contract, the AI-native constitution and `git diff --check` passed.
Only temporary SQLite fixtures were used; no external service or production
database was touched.

## 2026-10-20 Issue #17 FIX-029 — preserve unknown historical import values

The existing `historical_data_importer.py` now preserves unknown source values rather than defaulting them to neutral/low/zero and preserves caller transaction ownership and partial-commit truth. `tests/test_historical_data.py::TestImportTruthfulPersistence` passed **5 tests**. `python -m py_compile historical_data_importer.py tests/test_historical_data.py` and `git diff --check` passed. The broader `tests/test_historical_data.py` run on this branch produced **32 passed, 3 failed** (`TestSubjectFilter.test_cth_hit`, `test_exclude_veto`, `test_subject_recorded`); exact main SHA `3f6d67785752b465b5b022847cbbe75a55e1eb47` produced **27 passed, the same 3 failures**, with matching assertions. Their shared cause is that `subject_rules.get_active_brand()` intentionally returns no selected brand in these legacy tests, so `get_brand_config()` supplies empty focus words while the tests assume Guangzhou is the default. These unrelated failures remain open; the targeted five-test result is the FIX-029 evidence. Isolated synthetic data only; no production database or import was run.

Follow-up regressions now cover missing-ID results as NOT_WRITTEN, rollback of an importer-owned outer transaction, preservation of a transaction already owned by its caller, and SQLite RAISE(ROLLBACK) aborting a multi-row batch. A transaction-wide abort stops later rows; pending inserts are no longer counted as inserted, and even a malformed unprocessed value is returned as NOT_WRITTEN. The six focused cases in
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_historical_data.py -k 'log_failure_rolls_back_importer_owned_transaction or failure_preserves_a_transaction_owned_by_caller or missing_note_id_reports_not_written or batch_wide_sqlite_rollback or caller_connection_remains_uncommitted or batch_owner_commits'`
passed. Compilation, the governance machine contract, the AI-native constitution
and `git diff --check` passed. Tests use temporary SQLite fixtures only.

The review follow-up also covers FIX-029's isolated-first-row failure: a
per-record rollback stops the batch only when earlier pending writes were
invalidated by a transaction-wide rollback. Parameterized nonnumeric-metric and
SQLite `RAISE(ABORT)` cases now continue to a later valid row; the original
`RAISE(ROLLBACK)` batch test still stops and reclassifies pending writes. The
focused `TestImportTruthfulPersistence` class passed **10 tests**; compilation
and `git diff --check` passed. Only temporary SQLite fixtures were used.

## 2026-10-20 Issue #17 FIX-027 — Git diagnostics preserve unknown and failure

`lumenis_agg_api.py` reports Git state only from successful command output, does
not infer a clean tree from failed status reads, and sanitizes remote diagnostics
without stripping `@` from ordinary local paths. Regressions use a temporary local
Git repository and cover failures, URL/SCP and remote-helper credentials, opaque
helper fail-closed behavior, sensitive query removal, remote sanitization errors,
and `/srv/git/team@archive/repo.git`. Exact-head offline
command:
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_runtime_api_diagnostics.py` — **21 passed**. `python -m py_compile lumenis_agg_api.py tests/test_runtime_api_diagnostics.py`, governance machine contract, AI-native constitution and `git diff --check` passed. Temporary local Git fixtures only; no real remote repository or production system was accessed.

## 2026-10-20 Issue #17 FIX-025 — official-name evidence and exact scope

`subject_registry.py` uses the canonical Evidence bootstrap for unversioned
registries, retains migration ownership for versioned databases, binds official
names to the resolved CTH subject or BMP BrandFocus, records before/requested/after
keyword values, and rejects credential-bearing or sensitive-query source URLs.
Focused regressions are in `tests/test_subject_registry_official_name.py`,
subject batch concurrency/revocation tests, and
`tests/test_e2e_new_subject_flow.py`. `lumenis/shared/evidence/store.py` now
preserves an explicit SQL `NULL` for an unassessed `authenticity_score`, so the
legacy `DEFAULT 1.0` cannot turn unknown into a score; explicit `0.0` remains a
numeric value. `subject_registry.py` records an unassessed official-name source
as `NULL` while its recorded state remains `NOT_ASSESSED`.

The reviewed `--apply` official-name path now also retains the exact successful
Permission audit ID and caller in the signed Evidence inputs. An allowed result
without a non-empty audit ID is refused before the first registry write. The
isolated regression covers both the signed audit linkage and fail-closed
missing-receipt behavior; no approval token is copied into Evidence.
Credential query names are normalized across separator/case variants and reject
generic secret fields such as `secret`, `client_secret`, and `private_key`, while
ordinary campaign/source query names remain available to the provenance path.

The PR #90 query-validation follow-up also inspects bounded nested query values
and semicolon-delimited assignments before persisting the source URL. The
synthetic `redirect=...access_token=...` and `campaign=x;client_secret=...`
forms are rejected before any Evidence write; ordinary campaign parameters
remain accepted. On the candidate based on review head `6480017972c8e46721cf69b6b88a2440cef8350e`,
offline `tests/test_subject_registry_official_name.py tests/test_subject_registry.py`
passed **47 tests** with no background-thread leak. `py_compile` and
`git diff --check` passed. Temporary database fixtures only; no source or
production database was accessed.

The exact-head offline command for those four modules passed **21 tests** with no
daemon-thread leak. The test-only E2E fixture installs a synthetic HMAC key in
its isolated process environment so the pre-existing Evidence signature gate
remains enforced; no production key/configuration is read or changed. The
canonical Evidence regression command covering
`tests/test_shared_database_evidence_integrity.py`,
`tests/test_evidence_scoped_write.py`, `tests/test_evidence_chain.py`, and
`tests/test_evidence_write_failed_health.py` passed **84 tests**, also with no
daemon-thread leak. The changed Python files compile and `git diff --check`
passes. All database writes used per-test temporary databases; no production DB
or external source was used.

After the audit-linkage and query-secret follow-ups, the focused official-name,
registry and synthetic E2E command passed **42 tests**. `py_compile` and `git diff --check`
passed on the follow-up files; no production database or external source was
used.

The batch review follow-up also preflights each domain and subject ID before
approval or any row write, in addition to validating the full source URL and
official-name payload. This prevents a later missing or cross-domain subject
from leaving an earlier row written. The offline command
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_subject_registry_official_name.py tests/test_subject_registry.py`
passed with no daemon-thread leak. `py_compile`, the governance machine
contract, the AI-native constitution and `git diff --check` passed. Only
temporary database fixtures were used; exact remote checks remain separate.

## 2026-10-20 Issue #17 FIX-101 — close redirect bodies before Session hooks

The existing `PublicSourceHTTPAdapter.send` now closes every 3xx response
before returning it to `requests.Session`. Session response hooks execute before
`fetch_public_url` receives the response, so this prevents a caller hook from
consuming a redirect body before the existing redirect target/address and final
response-size checks. The outer redirect validation, pinning and bounded final
body read remain in place. Regression: `tests/test_public_source_transport.py::test_redirect_body_is_closed_before_caller_response_hooks` checks that an
offline response hook sees an empty, closed redirect; Requests can still prepare
the next request and the redirect body is never read. `UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --no-project --with pytest --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_public_source_transport.py` — **24 passed**. Full `tests/test_public_source_adapters.py` — **22 passed**; `tests/test_public_http_article_extraction.py` — **11 passed**; five focused RSS nodes — **7 passed**. Changed-file `compileall`, governance machine contract, AI-native constitution and `git diff --check` passed. No live network was used. The body is not drained; redirect response headers remain available to Requests. Remote required checks, real-network behavior and product acceptance remain separate and unverified.

## 2026-10-20 Issue #17 FIX-094 / FIX-102 — public source content and lineage

The existing `lumenis/system/collector/adapters/public_http.py` now retains
each independent best-priority semantic article block rather than selecting
only one same-priority block, while nested semantic blocks are included once.
Each public HTML item records selected locators,
the full selected-text hash/character count, returned preview length,
truncation/completeness state and response-document hash/byte count. The
existing 16,000-character output bound remains; meta description is explicitly
an excerpt and incomplete-body fallbacks are labeled. Safe transport still
limits the document to the existing 2 MiB bound.

The existing `web_discovery.fetch_google_news_rss` path uses
`public_source.fetch_public_url` with the existing maximum response size and
`google.com` host boundary instead of a separate direct HTTP call. Offset-aware
RSS dates are normalized to UTC in `published_at` for chronological sorting;
`source_published_at` preserves the source literal and offset. Naive or
unparseable values remain unknown with the source value retained. Stable
source URL, original publication date and time state pass through
`WebRSSAdapter`, alongside the existing
sanitized request/final URL and access/license provenance. HTTP failure,
unsupported media type, an empty successful feed and a safe-transport failure
remain separate states.

Follow-up review found that non-2xx responses are rejected inside
`fetch_public_url`, before the former RSS status branch could run. The transport
now raises `PublicSourceHTTPError` with its exact integer status; the existing
RSS result and `WebRSSAdapter` metadata preserve `HTTP_503` / `http_status=503`.
The status discriminator lives in the existing `except Exception` branch at
`web_discovery.py:239–246` (the HTTP-status check is at lines 241–243).
The regression goes through the real `fetch_public_url` and
`fetch_google_news_rss` path and fakes only the lowest `HTTPAdapter.send`
response. The unsupported media-type comparison remains a separate 200 response.

Offline combined command covering `tests/test_public_http_article_extraction.py`,
`tests/test_public_source_adapters.py` and `tests/test_public_source_transport.py`
— **67 passed** (14, 29 and 24 by module). The FIX-102 article-text follow-up
corrects `_iter_node_text_parts` in `lumenis/system/collector/adapters/public_http.py`:
BeautifulSoup's `stripped_strings` yields plain strings without ancestor links,
so nested page chrome was not filtered. Extraction now checks each descendant
text node's parent chain before normalization. The new offline regression nests
large nav/footer/header/aside/form/noscript/ARIA-navigation text inside an article
and verifies none enters returned text, hash, length or completeness. Changed-source `compileall`,
governance machine contract, AI-native constitution and `git diff --check`
passed. The tests use offline fixtures; no real public source was contacted. PR review, exact-head
remote checks and live provider/runtime/user acceptance remain separate and
unverified. Other Issue #17 items remain open.

FIX-094 fallback follow-up: `test_document_fallback_keeps_visible_layout_text_but_excludes_executable_markup`
confirms the existing document-body fallback retains visible header/page copy
while excluding script and style payloads. Re-ran the same offline combined
pytest command above; all three modules passed with no background-thread leak.
The added fixture is synthetic; no public source was contacted. Exact-head
remote checks and product acceptance remain unverified.
The accompanying source correction also rejects a script, style, noscript or
template node when that node itself is passed as the extraction root, including
the chrome-inclusive layout-text path; the focused regression covers all four.
Locator metadata is now bounded to 512 characters per path and 16,384 total
characters per capture; oversized locator values are shortened with a hash,
and omitted locators are reported with an explicit truncation marker/count.
An initial 80-article fixture did not exceed the total cap; that test setup
failure was retained and the synthetic case was expanded to 200 articles. The
focused regression then passed, verifying preserved source content and both
locator limits.
The RSS result now stores timezone-aware `published_at` in UTC while keeping
the original literal and offset in `source_published_at`. The combined offline
public-source extraction/adapter/transport suite passed after this correction;
changed-file `py_compile`, governance machine contract, AI-native constitution
and `git diff --check` passed. Shared Database's persisted mixed-format
`get_web_mentions` ordering remains OPEN because its original Owner and shared
write reservation are not available in this worktree.

## 2026-10-20 Issue #17 FIX-030 / FIX-031 — quality rule and enrichment truth

The existing `data_quality_gate.py::_finite_number` keeps integer bounds exact with finite `Decimal` comparisons, and `DataQualityGate.validate` evaluates a rule's condition before diagnosing an unknown rule type. The existing `database.py::insert_note` enrichment failure path remains a soft write but now persists `data_quality_status="error"` and clears a stale score. Regressions cover both sides of a conditional future rule, min/max bounds above 2^53, and an existing `ok`/100 note refreshed by a failing validator becoming `error`/NULL. `tests/test_data_quality_gate.py` passed **30 tests**; combined with `tests/test_database_insert_note_transaction.py`, **38 passed** using the offline cached pytest environment. `python -m py_compile database.py data_quality_gate.py tests/test_data_quality_gate.py`, governance machine contract, AI-native constitution and `git diff --check` passed. The database regression uses an in-memory SQLite database; no production database or external effect was used.

## 2026-10-20 Issue #17 FIX-055–057 — bounded GitHub source paging

The existing `github_connector.py` now bounds collection paging and response
size, binds continuation cursors to the request and repository allowlist,
preserves unread within-page results through a cursor offset, and validates
provider totals for resumed segments. Malformed URL ports become bounded
connector errors. It preserves partial results with explicit incomplete
coverage and distinguishes authentication, ordinary permission denial and
rate limiting. Redirects are checked before bearer credentials can be forwarded. The existing collector
adapter exposes coverage and safe cursor state; the GitHub Skill/MCP contract
was corrected to match those paths and boundaries.

Offline regression command:
`PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/-QTsH0Xz_HA1q_rC/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_github_connector_adapter.py tests/test_github_status_verification.py tests/test_account_skill_execution_scope.py tests/test_lumenis_shared_skills.py`
- **57 passed in 0.99s** across adapter/status and related account/skill modules;
no background-thread leak. Added regressions confirm a page-limit continuation
including `limit=60 / total=100` returns every provider item exactly once,
continuation totals expose missing pages, and malformed ports return a bounded
pagination error. `py_compile`, governance,
constitution, takeover governance and `git diff --check` passed. Tests use offline
synthetic responses; no live GitHub request was made.

Formal task/Evidence/UI wiring, persistent actor/task/source-version-bound
pagination, OAuth callback/revocation, and actual repository permission remain
OPEN or NOT_VERIFIED. `account/api.py` remains untouched because the exact
shared write reservation is unavailable.

## 2026-10-20 Issue #17 FIX-035 — distinguish empty XHS results from network failures

The existing `xhs_cookie_bridge.py` now applies the first BLOCKED/CAPTCHA/AUTH_FAILED pacing reduction immediately before continuing to another keyword, while suppressing a second task-summary report so one task still creates one risk event. `EMPTY` counts as a valid response in both the existing `network_adaptive` and `adaptive_engine` feedback paths. Regressions assert that the next search observes reduced pacing, the task records one risk event, and an EMPTY worker reports success with no error. The offline combined command across `tests/test_xhs_network_outcome_reporting.py`, `tests/test_xhs_child_worker_environment.py`, `tests/test_xhs_approved_local_worker_route.py` and `tests/test_xhs_lineage_persistence.py` passed **67 tests** with no thread leak. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. Fixtures only; no real collection or account access was performed.

## 2026-10-20 Issue #17 FIX-028 — count newly synced resources only

`resource_library.py` reports the count of resources newly added by the current
sync operation, rather than the full retained library size. Existing resources
and normal sync behavior remain intact. Regression: `tests/test_resource_library_sync.py`.
Exact-head offline command:
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_resource_library_sync.py` — **1 passed**.
`python -m py_compile resource_library.py tests/test_resource_library_sync.py` and
`git diff --check` passed. This focused result does not claim a full library or
product acceptance run.

## 2026-10-20 Issue #17 FIX-096/098/099/105/106 — platform adapter outcomes

The existing Facebook/X, Instagram, XHS and WeChat adapters now retain bounded
failure/verification facts and source identity, redact unsafe exception or
page data, and preserve explicit status instead of collapsing configured
failure into success or an opaque message (FIX-096/098/099/105/106). These
changes stay in their existing adapters and test owners; no collector,
secondary collection, API composition or product module was added.

This follow-up keeps each original issue ID at its source owner: FIX-096
sanitizes the terminal X detail failure in
`lumenis/system/collector/adapters/x_platform.py`; FIX-098 accepts a Facebook
read-more control only after the exact native post body grows in
`lumenis/adapters/facebook.py`; FIX-105 distinguishes missing Instagram worker
configuration, provider/kernel unavailability, and network failure in
`lumenis/adapters/instagram.py`, then maps raised comments/creator failures in
`lumenis/system/collector/adapters/instagram.py` through the existing status
mapper. Their regressions are in `tests/test_facebook_x_adapter.py` and
`tests/test_instagram_main_adapter.py`.

Exact offline focused commands on this candidate:

- `PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/-QTsH0Xz_HA1q_rC/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_facebook_x_adapter.py -k 'fix_098_facebook_ or fix_096_x_sanitizes'` — **8 passed, 33 deselected**.
- `PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/-QTsH0Xz_HA1q_rC/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_instagram_main_adapter.py -k 'fix_105_worker_configuration or fix_105_registered_instagram_raised_failures'` — **8 passed, 26 deselected**.
- `PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/-QTsH0Xz_HA1q_rC/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_facebook_x_adapter.py tests/test_instagram_main_adapter.py` — **63 passed, 12 failed**. Those 12 failures were reproduced on a clean main worktree at the exact baseline; no new full-module pass is claimed.

The 12 retained baseline failures are not silently counted as passing or fixed:
Facebook/X has `test_facebook_parser_preserves_long_body_and_metric_display_through_canonical_adapter`, `test_facebook_comment_body_is_not_truncated_or_assigned_zero_metrics`, `test_x_parser_keeps_the_complete_observed_long_post`, `test_x_parser_preserves_native_id_explicit_zero_unknown_counts_and_publish_time`, `test_x_metric_parser_falls_back_to_text_and_rejects_approximate_or_bad_grouping`, `test_main_facebook_adapter_constructs_search_and_detail_results`, and `test_main_facebook_adapter_errors_keep_platform_and_health_unverified`; Instagram has `test_status_mapping_success`, `test_status_mapping_blocked`, `test_status_mapping_collect_error_proxy`, `test_status_mapping_collect_error_other`, and `test_health_check_no_cookie_no_proxy`. They exercise pre-existing parser fixtures, worker setup, and search/health status expectations, rather than the changed X terminal-detail message, Facebook exact-post expander, or Instagram raised comments/creator exception paths. Those separate behaviors remain unclaimed here and should be routed to their own original owner if the unified register maps them to an active finding.

The earlier focused receipt remains: X read-only worker 24, XHS FIX-099 2,
WeChat public sources 17, and the prior FIX-105/FIX-098 cases; those plus this
follow-up are isolated fixture tests, not product acceptance. Python compilation,
`git diff --check`, governance machine contract, AI-native constitution and
takeover governance passed. No background-thread leak was detected. Real
browsers, devices and external collection remain NOT_VERIFIED.

FIX-100 remains OPEN because the `secondary_collection.py` write reservation
is unavailable. FIX-092/093/097 and `platform_naming.py` coordination remain
OPEN. Hidden/redacted XHS snippet effects, real devices, and external collection
remain NOT_VERIFIED; tests used injected/offline fixtures only.

## 2026-10-20 Issue #17 FIX-091 — Sogou challenge retry and link-resolution boundary

The existing `lumenis/adapters/sogou_search.py` recognizes explicit
verification/anti-bot challenge markers and returns `NEED_HUMAN_VERIFICATION`
as a failed result, stopping same-channel retry, the next channel and link
resolution. Link unwrapping now checks both response text and the final Sogou
anti-spider URL. It processes links in bounded batches, cancels queued work on a
challenge, and does not start a later batch; requests already running in the
current batch may finish. `_resolve_links` reports the challenge to `search`,
so the provider failure cannot be reported as a successful collection. The
normal JS redirect path, ordinary empty search success, bounded ordinary retry,
and a distinct explicit search after the fixture clears the challenge remain
available.

Follow-up against exact prior PR #87 head `a0c5f50f400ceb3bf0805d53614cec999aac2852`
verified three conditional review cases (not evidence of a live-provider
incident): discussion `r4321123508` showed that a verification form after the
first 4,000 characters was ignored and could yield an EMPTY result;
`r4321123513` showed relative and protocol-relative JS literals were not
resolved; `r4321123518` showed a normal `/articles/captcha-design` path could
be misclassified. The existing detector now scans the full returned response.
Redirect literals are parsed statically and resolved against the response URL;
only credential-free HTTP(S) targets are accepted, and JavaScript is never
executed. Challenge recognition is limited to complete root path segments
`/antispider`, `/verify` and `/captcha`, so article slugs remain ordinary links.
Regression covers the exact late form through both `collect` and registry,
nine redirect-target inputs through both entrypoints, ordinary article and
absolute redirect controls, and `javascript:` / `file:` rejection. It verifies
the intermediary URL stays in place when a target is rejected or challenged.

Cross-PR review also found that a prior empty/non-empty cached result or custom
fallback could turn a Sogou challenge into success, including after repeated
challenges opened the adapter breaker. PR [#85](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/pull/85) now guards terminal provider errors at the existing `BaseAdapter` fallback and open-breaker paths, retains the last provider cause while requests are blocked, and clears that state only when a new permitted request provides recovery evidence. Its regressions cover empty/non-empty cache, custom fallback, threshold opening, the no-request breaker shortcut, explicit recovery and ordinary transient fallback after breaker opening. PR #87 is stacked on the updated lower-adapter commit and adds public `collect` regressions with one complete `AdapterCacheContext` across prior empty/non-empty success then challenge, ordinary same-context network fallback, and `registry.search_all_with_status` reporting `FAIL`. Review also found two Sogou classification boundaries: the generic word `验证码` in an ordinary article is no longer a challenge/block marker, and rate-only `访问过于频繁` remains on the existing bounded retry path rather than manual verification. Both final channel URLs and JS-extracted destinations are now checked for Sogou verification paths; public `collect` and registry tests cover `/captcha/` without executing JavaScript or issuing another request. The W6-owned API/UI projection remains unmodified and unverified; remaining Issue #17 work remains open. At PR #87's initial submission, its restricted regression command passed (**25 passed**) and `tests/test_adapter_resilience.py` passed (**30 passed**); that result describes the earlier test set only. Existing tests include redirect challenge stopping later queued links, ordinary JavaScript redirect resolution, breaker-open terminal preservation and ordinary cached fallback after breaker opening. Full-file, exact-head CI/review, real-provider, runtime and user acceptance were not claimed. No live source or external effect was used.

On the updated combined stack, full `TestSogouSearchAdapter` passes **63
tests**; `tests/test_adapter_resilience.py` passes **30 tests**. Changed-source
compilation, governance machine contract, AI-native constitution and `git diff
--check` pass. These remain offline source regressions; exact-head remote checks,
real Sogou behavior, W6-owned projection, runtime and user acceptance remain
unverified.

## 2026-10-20 Issue #17 FIX-107 / FIX-108 — pitch export and report readback

The existing `scripts/pitch_export.py` sets Normal paragraph-after spacing to
6 pt and removes template Title borders from both the style and direct title
paragraphs for ordinary and audiovisual manuscripts (FIX-107). The existing
`lumenis/shared/reporting/source_brief_job.py` attaches only evaluations whose
stable ID, artifact, actor, scope, source/evidence references, fields, metadata
and parseable ISO-8601 timestamp match the reopened report. Invalid or absent
rows remain pending; explicit resume cannot label an incomplete readback as
recorded. Report listings reuse those validated records and state instead of
reattaching a mismatched row by stable ID. GET remains read-only (FIX-108).
Existing `operational_brief.py` evidence/rights/source checks already cover the
inspected path and required no change.

Related offline regression command:
`PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/4N-meRHHaGHjU5wZ/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_pitch_export.py tests/test_source_brief_job.py tests/test_source_brief_job_routes.py tests/test_scoped_source_brief.py tests/test_entity_profile_lifecycle.py tests/test_source_brief_tasks.py tests/test_source_brief_listing.py tests/test_internal_pitch_shared_av.py tests/test_internal_pitch_workflow.py`
— **297 passed in 42.06s**, including regressions for explicit recovery with an
invalid timestamp and consistency between reopened reports and listings.
`py_compile`, `git diff --check`, and local
LibreOffice DOCX→PDF rendering for normal and AV manuscripts passed; generated
artifacts were removed. No external model, production database or external
effect was used. Exact write reservations remain unavailable for the separate
`experience_runtime.py`, `saved_work.py` and `app.py` integration paths, so
those FIX-108 owner/caller checks remain OPEN; runtime and user acceptance are
NOT_VERIFIED.

## 2026-10-20 Issue #17 FIX-047 — preserve saved detail during backfill failures

The existing `topic_note_detail_backfill.py` distinguishes failed, empty and available fields, merges only nonempty verified values into the exact row, and derives quality from the merged stored detail. Failed extraction cannot erase saved content/media/comments; oversized JSON is rejected intact and commit ownership remains with its caller. Supplied verified JSON fields now bypass parsing corrupt legacy values; unchanged verified payloads still recalculate stale quality, while partial merges preserve the prior aggregate capture timestamp. `tests/test_topic_note_detail_backfill.py` passed **9 tests**. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. Tests use an in-memory database and synthetic pages; no CDP, live collection or production DB was used.

## 2026-10-20 Issue #17 FIX-058 / FIX-060 — derived memory TTL and forget

In the existing `agent_memory/base.py` owner, expired records are filtered
before the caller limit and use one query-time clock value (FIX-058 E04-TTL).
The existing derived-memory writer rejects a delayed implicit same-task/key
write after the forgotten tombstone, rather than reviving that record
(FIX-060 E04-FORGET). A user correction can intentionally restore a forgotten
key only by matching the tombstone's current revision; stale revisions conflict.

`PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/4N-meRHHaGHjU5wZ/lib/python3.12/site-packages python -m pytest -q tests/agent_memory/test_working_memory.py`
— **20 passed**, with no background-thread leak. The isolated FIX-060 SQLite
regression confirmed the forgotten revision/tombstone rejects the stale write
and remains unreadable after reopen. `compileall` and `git diff --check` passed.
The full API/Agent regression module, including the FIX-058 TTL case, then passed
with the existing offline `feedparser` cache:
`PYTHONPATH=/tmp/lumenis-uv-cache/archive-v0/-QTsH0Xz_HA1q_rC/lib/python3.12/site-packages python -m pytest -o addopts='' -q tests/test_scoped_derived_memory.py`
— **12 passed in 12.58s**, with no background-thread leak. No package was
fetched or installed. Wider derived-dependency invalidation remains OPEN for
FIX-060. FIX-059 still lacks a verified Agent retrieval/fusion caller; FIX-061
and FIX-084–088 remain OPEN because their Shared Learning files have no
available exact write reservation.
No W6 or production database was modified; runtime/product acceptance remains
NOT_VERIFIED.

Review follow-up at the PR branch head: `agent_memory/base.py` now preserves the
existing `_query(filters, limit)` subclass call signature while passing the
same TTL clock through a context-local value to the base implementation.
`LearningMemory` in the separate Shared Learning owner therefore keeps its
existing override unchanged. The prior review reproduction
`TestLearningMemory.test_positive_negative_samples` and a regression for the
legacy override plus single-clock TTL ordering pass (**2 passed in 0.21s**).
The broader combined run of `tests/agent_memory/test_learning_memory.py`,
`tests/agent_memory/test_working_memory.py` and
`tests/test_scoped_derived_memory.py` passed **52 tests in 13.39s**, with no
background-thread leak. A follow-up exact API regression verifies stale
revision rejection and explicit restoration at the current forgotten revision;
the same combined command now passes **53 tests in 14.24s**, with no
background-thread leak.

## 2026-10-20 Issue #17 FIX-026 — incomplete source availability stays unknown

`data_query_api.py` keeps source counts/availability unknown when a source result
is incomplete or capped, instead of interpreting the visible partial count as a
complete total. Normal complete and explicit-zero paths remain distinct. The
focused regression is `tests/test_data_query_source_limit_semantics.py`. Exact-head
offline command:
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --offline --no-project --with pytest --with flask --with requests --with beautifulsoup4 --with feedparser python -m pytest -q tests/test_data_query_source_limit_semantics.py` — **4 passed**.
`python -m py_compile data_query_api.py tests/test_data_query_source_limit_semantics.py`
and `git diff --check` passed. These isolated tests do not establish live-source
coverage or product-level acceptance.

## 2026-10-20 Issue #17 FIX-038 — verify recovery against the affected notes database

The existing `auto_recovery.py` verifies the notes-table invariant against the same resolved database path being recovered; a generic `SELECT 1` can no longer label a missing notes table fixed. `tests/test_auto_recovery_database_truth.py` passed **3 tests**. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. Tests use temporary SQLite only; no production recovery was executed.

## 2026-10-20 Issue #17 FIX-090 — search HTTP result truth

The existing Baidu and Bing search adapters now call `raise_for_status()` before
parsing a response, so an HTTP error page remains a failed result instead of
becoming a successful empty result. The existing `search()` error contract and
normal HTTP 200 empty-result behavior are preserved. `tests/test_adapter_http_truth.py`
covers both adapters against HTTP 503, ordinary HTTP 200 with no matches, and a
transport timeout (6 passed) using offline response fixtures; no live source was
queried. Verified with
`UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --no-project --with pytest --with requests python -m pytest -q tests/test_adapter_http_truth.py`
(6 passed), `python -m compileall -q lumenis/adapters/baidu_search.py lumenis/adapters/bing_search.py tests/test_adapter_http_truth.py`, and
`git diff --check`. This closes only the adapter-level state distinction in
FIX-090; the W6-owned HTTP/API projections, live-provider behavior and actual
collection remain unverified, and all other Issue #17 outcomes remain open.

## 2026-10-20 Issue #17 FIX-049 — normalize ROI using both currencies

The existing `ad_intelligence/platform_registry.py` computes each platform's rate as source-rate divided by the requested base-currency rate and rejects an unsupported base currency instead of returning an implicit fallback. `tests/test_platform_registry.py` passed **14 tests**. Changed-source compilation, governance machine contract, AI-native constitution and `git diff --check` passed. Tests use fixed synthetic rates; no live exchange rate was fetched.

## 2026-10-18 source-adoption validation handoff

Existing CTH/BMP/Shared/SYSTEM Owners now carry the source-level research,
reference lifecycle, business review and local contribution capabilities. The
single planning/screen-specification chain and all original requirements remain.
Evidence: [source-adoption validation receipt](evidence/round-15/source-adoption-20261018/VALIDATION_README.md).
The 4003-file tested source is preserved byte-for-byte for product and tests;
this packaging adds documentation/evidence only. Static gates and six same-source
real TCP nodes passed. The unified regression finished with 4087 passed, 6 deselected, 318 subtests passed
in 556.07 seconds; all six deselected TCP nodes passed separately on the same
source. Logs and prior failures are preserved. This record does
not claim this candidate is published, remote checks passed, four-surface UI
acceptance, external delivery, production activation or business results.

## 2026-10-17 README engineering-guide navigation

The Product Owner approved one bilingual navigation note in the root README:
link the existing `.codex/README.md` and state that workstation hook registration
and trust remain separate from pulling or merging source. This co-published
record satisfies the existing documentation-publication contract; it changes no
product requirement, task dispatch, model selection or runtime state. The first
README-only check failed because CURRENT was not co-published; that failure is
retained, and the validator is unchanged. Required checks and exact main readback
remain necessary before treating this documentation update as published.

## 2026-10-17 PR79 cloud repair verification

The Product Owner explicitly requested repair of PR79 in the cloud, followed by
integration with current main and merge only after the required checks pass.
The repair preserves the complete product plan and all existing main status and
protected-candidate records. It changes engineering continuity tooling only;
no production runtime, database, workstation hook registration or product-release
acceptance is implied.

The nine latest review findings and one source-path normalization defect now have
focused regressions: fresh PO turn identity even for identical text; bounded Stop
continuation provenance; ignored owned-source changes; immutable pending-effect
admission versions; changed authority at non-closure exits; structured-record size
budgets; explicit dependency waits; intact deferral IDs; immutable blocker/resume
conditions; and equivalent scope path aliases. The original candidate fails the
new regression cases; those failures remain evidence, not erased test history.

The merged-source candidate passed all 193 engineering-helper tests in the cloud
with pytest available, with no skipped tests. The three changed Python files pass
compilation and full Ruff. These are isolated tooling checks, not native Windows
runtime activation or whole-product E2E. Missing trusted Stop metadata fails closed;
legacy pending effects lacking their admission pins require reconciliation and
must never be replayed or assigned fabricated source history. Required remote
checks and exact merged-main readback remain separate publication conditions.

## 2026-10-16 M completion guards and current authorized scope

The direct PO instruction requires the existing development hooks to constrain
silent scope reduction, deferral of authorized missing capabilities and premature
completion. The existing Owner continuity record carries the complete outcome,
stable requirement IDs, coverage and versioned real-operation/recovery receipts;
the single `.codex/hooks/lumenis_hooks.py` handler checks those records, rejects
closure with remaining work, compares normalized complete scoped inputs, and
retains unchanged-scope receipts across unrelated commits. Explicit source-pinned
PO deferral is a non-closure exit. Frozen IDs and implementation paths survive
context clear; record switching revalidates current prior closure, and any new
direct instruction requires reconciliation before a terminal exit. Fresh execution
bindings require RUNNING unfinished work, rather than renewing historical terminal
records. Report-only snapshots include the bound record and pinned evidence, even
when ignored by Git or retained after context clear.
Non-closure exits retain their authorizing prompt and immutable proof identity;
rewriting their description does not renew an old blocker or deferral. Pending
external effects remain in the same append-only continuity ledger until a
hash-pinned terminal readback resolves them. Structured outcome evidence has a
separate bounded budget so a complete task can retain all 100 supported outcomes.
English and Chinese pause/approval instructions preserve unfinished outcomes. Hook
configuration follows the current task and actual evidence, never historical
window/model state. See `.codex/README.md` for its schema, bounded Stop behavior,
native activation and rollback. Neither a hook PASS nor a source publication
establishes product acceptance.

The current hook candidate preserves the complete admitted outcome through context
changes, explicit PO deferral and pause. It verifies large owner records with the
same bounded budget on save/read/Stop; deferral requires the current real PO
prompt and exact requirement IDs. Pausing stops execution without rollback and
records any post-pause scoped changes for reconciliation. Reopened outcomes
reserve fresh outcome/recovery receipts, path aliases normalize consistently,
and duplicate receipt references are rejected before cached validation.

The prior complete engineering-helper run passed 166 tests plus 69 subtests.
Subsequent focused checks covered the record/deferral changes and fourteen
pause/capacity/path/cache cases; compilation and full Ruff passed for the changed
Python files. Prior failed CI and fixture failures remain historical failures;
only the exact updated commit's required checks qualify its publication. These
are development-tool results, not workstation activation, product E2E or release.

The direct PO instructions dated 2026-10-16 covered three reported upgrades:
all relevant issue #17/Slack updates and research adoption; all approved Cortech
capabilities except its Muse account implementation; and full REA reinspection
and usable adoption of the original applications/sites. REA must serve both
platform-specific acquisition improvements and missing product operations and
capabilities. Preserve every original object and requirement, source/permission
boundaries, independent Shared creation, AI-independent basic work and the four
approved surfaces. The task history also records a later direct PO assignment
for frontend-plan/text-sketch consolidation, pixel/code research and subsequent
REA investigation, without frontend construction in that assignment. Its intended
outputs are the existing unique complete plan and sketch documents plus validated
capability handoffs for product implementation and integration.
REA covers underlying capability logic, page layouts/elements and more complete,
accurate acquisition, followed by actual product improvements. These dated scope
records prescribe no current start, pause, dependency order, window or model.
Each task follows its newest applicable direct PO instruction and local readback;
publication cannot suspend independently authorized work or resume historical work.
Subsequent outcomes need
actual input, useful output, save/revise/reopen/recovery and loaded-version
evidence through existing owners. PR #77/#78 remain bounded integrated repairs,
not completion of these three upgrades. Current implementation, runtime and
acceptance observations stay separately traceable in the existing Owner records.

## 2026-10-14 research adoption (documentation, not runtime acceptance)

The six PO-supplied OSS repositories were reviewed at fixed commits, including executable implementation/skill material and licenses, rather than star counts. Existing plan G109/G130/G159/G163, media steps E1/E8 and Experience's result-visualization clauses carry the bounded adaptations; the third-party register holds all six source pins, exclusions and acceptance conditions. Artcraft contributes editable-state/readback and stale-result fencing ideas; Anatomy/Diagram Design contribute data-consistent explanatory graphics; Matt Pocock's skills contribute interface/recovery review; Hyperframes is an optional HTML-video adapter candidate; AirLLM is a conditional exact-model resource experiment, not an installed provider or proven low-memory solution. No upstream code/assets, dependency, model weights or service were installed/copied by this research publication. Product bindings and actual outcomes remain OPEN, existing motion remains intact, and no window is dispatched.

The existing prelaunch review now consistently includes optional account/login/settings and both developer modes in engineering closure, including its Website/ACC-01, SYS-04 user mode and SYS-07 founder mode rows. ACC-04 keeps Permission recovery action-local, using only server-returned callbacks; account settings never grant access. Old account deferral/exclusion sentences were replaced in place. Server Permission and ordinary open-workspace access remain. This is documentation convergence, not login implementation or user acceptance.

The complete visible PO engineering image (items1–7/9/10/13–15 and introduction) is mapped into existing plan§17 and G108/G109/G187. Fixed Claude/OpenAI/Grok source, official Muse engineering and MCP/PII/voice/DPO documentation distinguish reusable mechanisms from unsupported ratios, service rights and unimplemented outcomes. Existing Task/Memory/Gateway/Permission owners remain; no second runtime, automatic training, model switch, OS control or public export. Original motion is unchanged. SOURCE here is research/rule adoption; all associated new runtime/outcome claims remain NOT_VERIFIED.

PO transitions-ui-generation is adopted in Experience §19 and the existing CTH-10 plan/spec/third-party register. The additive SourceBrief reveal is selectable and skippable, runs once only for a newly generated result after persistence readback, and preserves all existing motion, timing and preferences. A fixed skip slot prevents layout shifts; reveal waits for stable registered-font paragraph layout, while unregistered dynamic fonts show the result immediately without the effect. Full choice preserves user motion; Follow System honors OS reduction. Scroll, pointer, keyboard, semantic actions (including Read Aloud), lifecycle and font changes cancel playback or pending preparation, even while the preference is loading. Scheduled frames prevent idle preparation hangs. Evidence: [Flutter engine font-manifest initialization](https://github.com/flutter/engine/blob/af7e796e161ae0bb1ff0758c71a7105418bd9ded/lib/web_ui/lib/src/engine/initialization.dart#L159-L224) and [Flutter font-change notifications](https://github.com/flutter/flutter/blob/6a19cca56475dbfba1478ee68d7bd0c2ef891da1/packages/flutter/lib/src/painting/binding.dart#L170-L182). Targeted regressions: 38 passed; Flutter analysis and Web build passed. Experience and AI-native gates passed for this source commit. Live Core generation, Runtime load and user acceptance remain NOT_VERIFIED.

The remaining 18 brand, 2 KDRAMA, 15 XHS, 3 case-benchmark documents and adoption lines480–742 were read in full at the stated scope; line743 is absent. All26 fixed local mathematics transcripts were read through appendices/references. The existing coverage record lists paths, boundaries and adoption. Original research/history stays intact. Product-plan G78/G81/G99/G102–104/G109/G111/G143/G158/G160–164/G170/G182 now distinguish actual evidence, algorithm hypotheses, finite implementation, proof and model gains; G163 stays OPEN.

The PO's complete person-like-agent argument is mapped claim by claim in the existing plan§16, with official Bot/Muse/Instinct sources, fixed OpenClaw source and community observations. Existing Architecture/Experience and AI-01/SH-06/sketches carry responsive multi-task conversation, scoped memory, bounded delegation, completion readback and selective delivery. This publication adds no Runtime, provider, external IM, computer control or dispatch; async product operation and four-surface E2E remain NOT_VERIFIED until actual owner evidence exists. Paid-source access and model/training/deployment authority are unchanged.

## 2026-10-13 source observations (historical provenance)

The October 13 observations covered PR31's protected business-decision work, PR35's browser streaming, PR36's authorized subject-wide collection program, registry seed/relationship candidates, source/session samples, operational-inbox permission and decision-card gaps. Their original dated counts, paths, task IDs and failure evidence remain in Git history and the existing linked receipts. They are not a current task list, writer reservation, account deferral, frontend pause or deletion instruction. Current task scope and frozen/published source are recorded once in §1 below; Architecture/Owner/Experience and the complete plan retain all unfinished requirements. Protected candidates, old branches and originals are not removed by this documentation consolidation.

## 2026-10-13 SYS-06 built-in browser live stream (dated readback, PR #35)

Root internal_browser_stream.py moved to the single owner lumenis/system/browser/runtime/screencast_stream.py; new 
rame_stream.py streams frames of the isolated /api/browser/sessions/<id> page over SSE (/frames/stream, /stream-policy). PO defaults: page AI-readable OFF and nothing to Evidence unless registered; leaving the view pauses the agent on sensitive/logged-in pages (unknown login = logged in); during human takeover no frames to AI and none stored, only action receipts; isolated sessions without personal cookies. SYS-06 shows pushed frames with gaplessPlayback; human-control actions still use lease-bound single frames. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 AI-01 submit receipt read-back (dated readback)

AI-01 submit receipt: `POST /api/experience/ai/intent` reports `evidence_recorded` only after the Evidence owner reads back the record written for that exact `execution_id` (skill_execution source, source/task/trace bound to the execution, intact content hash, payload naming the execution). The execution chain's own ok flag alone is no longer trusted. No AI output, trace route or Evidence item is fabricated; the owned Gateway stays UNAVAILABLE, so real executions can still end not-completed. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 SH-06 read-only inbox backend (dated readback)

SH-06 read-only inbox backend: `GET /api/experience/screen/SH-06` now returns items only for a signed-in actor with a verified `operational_inbox` read grant (GLOBAL_ALL needs CTH and BMP global grants; FOCUS needs the exact Subject/BrandFocus). Each TaskEngine task must carry a matching stored row scope and a fully recomputed TaskEngine Evidence hash chain; it is emitted as row projection v2 (read_allowed, scope, evidence.canonical_reference, integrity v2 content-integrity-only, lineage_verified). Unverified tasks are dropped; the legacy global task/DLQ/health shape and all approve/assign/snooze/retry controls are gone. Without a grant the screen shows "通知与待办暂不显示". Notifications/alerts lanes stay empty until an owner emits verified items. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 AI-01 submit trusted FOCUS identity (dated readback, PR #40)

AI-01 submit identity (PR #40): the request body accepts only `task` and `action_type` (AI-01.md:56-57); other fields return 400. The execution domain/product comes only from the existing server-side scope resolver (`_content_project_scope`, FOCUS) through `domain_isolation.resolve_domain_identity` (CTH->CTH, BMP->ZBMP). GLOBAL_ALL or an unresolved scope returns `not_executable` (`AI_INTENT_FOCUS_SCOPE_REQUIRED`) without executing or writing Evidence. No account/auth configuration was added (BACKEND-GAP-029 remains for the full trusted adapter). Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 PO agent-role change (dated readback, not dispatch)

The direct PO clarified: Codex and Akang (GrokBot) are equal-level product-development agents; the PO alone partitions and dispatches their work. Brio (Muse) is the PO-only global-data-source research and verified acquisition-target inventory contributor, delivering one Markdown research handoff and then acting only on direct PO instructions. The operative routing is in `AGENTS.md` and the machine/source-owner contracts; this dated handoff is neither a new agent authority nor permission to run research, collection, code, training, payment, deployment or PR merge automatically.

## 2026-10-13 AGENTS LF pin and T04 structured red lines (dated readback)

`AGENTS.md` is pinned to LF in `.gitattributes`, so the Codex `project_doc_max_bytes` budget (131072, with 16384 headroom) is measured on the same bytes on Windows and in CI; the text did not change. The six T04 historical PO prohibitions are structured `red_lines` keys in the governance machine contract. The blocking validator `verify_governance_machine_contract.py` rejects dropping or allowing any of them. The PR #24 prose-anchor test has been replaced. AGENTS.md carries a one-line LF note so existing Windows clones rewrite it on update (PR #28 review). PO receipt: `PO-20261013-AGENTS-LF-AND-T04-STRUCTURED-RED-LINES`. 阿康（bot）

## 2026-10-13 PO direct overrides (supersede older text anywhere)

1. Auto-collection scope = all registered subjects (Taikoo Hui is a depth reference only, never the sole scope).
2. Collection runs headless in the background; platform login recovery uses the one in-product LumenisPlatformRecoverySheet on every surface; no automatic external browser window.
3. R&D-stage configuration and registry writes are executed directly by the developer (backup first); no PO approval wait.
4. Merge a PR once all required checks are green; no PO wait.
5. Brand names = official-site names with source URL.
6. The developer runs end-to-end tests for newly added subjects and keeps them in CI.
7. Retired product routes (Zhipu, Ollama, Jev, OpenCode, Ark, LM Studio, llama.cpp) remain inactive; do not restore their old calling code, probes or fallback. Keep the owned model goal, product-provided Groq connection and user BYOK connections to other providers behind the sole SYSTEM Gateway and existing configuration/secret/Permission owners. A retired route is not a permanent vendor-wide BYOK ban. Support each protocol and modality explicitly; validate destinations, actor isolation and exact external-send authorization. No unrestricted endpoint transport, implicit credential activation or automatic fallback is granted; actual implementation and user outcomes require current evidence.
8. In-loop: collection, CTH, BMP, Shared, AI, no-shell tools in built-in browser, chat UI cards, full Skill Store, GitHub connector, MCP, frontend functions, competitor proofs, accounts (free email codes/Google; Apple after developer-account activation; original settings presentation), user and founder developer modes, commercial-readiness items, visuals, logo, role art. Post-launch: real-user validation, paid/licensed sources.

## 2026-10-16 unique frontend plan and visual sketch (historical planning-only scope)

最新直接PO补充：两份主稿是持续演进、集中维护的工作基线，不冻结UI/前端或限制M当前及未来升级；后续获准改进在原Owner/合同内继续原位更新。本窗口的规划发布→REA次序不派工或暂停其他窗口。REA使用前须认真研究官方GitHub适用版本的文档、实际源码/测试、许可与发布差异，保留commit和阅读/验证边界。本窗口2026-10-16直接PO新增沉重弹性、磁吸、流畅、抛出及产品适配物理交互，要求质量/刚度/阻尼、吸附范围/力/阈值、释放速度/摩擦/边界恢复等参数真正参与计算并可测影响；已原位纳入Experience §19及两份主稿。保留原动效/用户选择/减少动态，逐表面实际参数接线、轨迹/性能/中断恢复仍OPEN；2026-10-16该文档批次未实现物理交互或新增引擎，当前获准建设按§1接续。

前端规划现仅使用[完整产品/前端规划](LOOP-PLAN-20261014/product-plan-full.md)和[唯一视觉文字草图](LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)。本次收敛保留全部195个G标识、原26个R/N/O有效要求、F0–F13完整建设分组与原研究指纹；覆盖Public Website、Web Workspace、Windows/macOS和iOS、44屏基线以外的完整用户工作、独立Shared研究/提案文稿/视频/播客、三语/无障碍/原动效/保存修订重开恢复。原21份ADD、分步稿和创作覆盖共23个重复活跃文件的有效内容已迁入，精确原文仍可在父版本Git历史查证，研究原件/资产/审批/失败记录未删。ScreenSpec保留独特Owner/API/Permission/SourceUse/字段/状态/动作/幂等/恢复/验收合同，布局指向唯一草图，不升级原设计或实现状态。

本任务窗口最新直接PO明确PixiJS用于过往参考网站/产品的提取、重建与前端校准，不采用像素画风。浏览器/REA负责真实可见结构/样式/状态取证，隔离PixiJS校准器负责几何重建/对照；不是新增产品renderer/采集真相或引入像素艺术。已完成8.22.0小型WebGL绘制/DPR/销毁探针；完整参考目标提取、对照校准、产品性能和四端运行仍未因此验证。2026-10-16直接PO给当前规划/REA窗口（private-source-id-sha256-be1add9d40399731d4b45de79092009a127762e625050a53cc69df7bc300c9ea）的两项任务以该质量次序执行；这是限定窗口的授权来源事实，发布/读回不派工、不恢复旧窗口，其他或后续窗口不可据此自行启动REA。

本次统一原唯一完整产品执行规划（前后端）和唯一四表面视觉操作草图，保留195个G、44屏合同、SYSTEM/CTH/BMP/Shared、Math/AI、媒体、采集、研究、账户/权限、恢复及全部资料和未完项，不另拆专项规划或队列。最新直接PO全产品语言纠偏落在规划§4.2、草图§1.4及Experience§22：操作页使用任务、内容、结果、行动和必要真实状态、错误、风险及权限文案；方法、算法、口径和引用按需查看，业务约束、覆盖缺口、误差与不确定性不能隐藏。普通研究资料直接上传导入、自动解析和无AI基础分析，模型增强独立可选；不设通用“来源使用/本次用途”表单，后台仍保留来源、Permission、权益UNKNOWN及真正敏感/额外用途的确认。资料库按实际入库时间组织，每份资料及分析各有卡片，关联原文/结果和版本并可修改、保存、重开、恢复，未知发布时间不由入库时间代替。鼠标如手的按压、拾起/轻倾、阻尼拖动、放手回弹和适用卡片翻转进入同一完整计划；实际参数须控制真实几何/轨迹，保留约90ms反馈、键盘/触摸/读屏等价、减少动态及原全部视觉/动效选择。当前ChatGPT Work/Grok Bot官方操作说明仅作ADAPT参考；REA/Pixi已得局部方法和V2包及全部未完恢复点归档于规划§20.4，不代表全包质量或产品验收。Experience仅§22作精确共享发布，产品树§19及其他dirty候选不复制。最新直接PO明确：当前整体前端不合格、尚未接受（NOT_ACCEPTED），需要继续重做不足部分、升级并按完整视觉/UI/UX/AIGC/动效及四表面范围验收；规划、文案、编译或局部操作通过均不能升级这一整体判断。2026-10-16该窗口收尾只整合发布文档，当时将完整前后端闭环留待后续派工，未继续REA或产品运行；该批生产Core/DB/模型/采集/训练/部署未执行的事实保留。2026-10-18获准完整开发与当前分工见§1，该旧收尾不再构成当前等待条件；原主工作区及其他窗口工作受保护。已集成源码、冻结候选与旧/未核运行分别报告，PR79及其hooks未合并/未核装载不能称上线。本条不暂停、派工或恢复其他窗口；文档检查不能代替真实用户成果、运行恢复、M接受或PO重复操作，完整产品仍OPEN。

本次规划审查同步补正：23个迁移来源记录Git blob原始字节SHA-256与明确标注的本机CRLF读取指纹；SYS-05保留BACKEND-GAP-040只读snapshot，ACC-04注明既有registry别名，BMP-08注明Shared/C4-W4制作Owner。既有隔离PixiJS小探针完整HTML源码/观察JSON原文以UTF-8/LF及HTML末尾空行规范化后，在round15研究文档代码围栏中发布，可按围栏正文哈希提取复原；原hash/围栏正文hash与未保留截图等限制明确，未重跑。该文档批次按RULES_ONLY_PUBLICATION校验，未发布可执行HTML或任意JSON路径；当前组合的发布状态须按实际变更和同版证据另核。草图链接仅为视觉规划输入，不替代Experience或本屏实际合同；触控、营销budgeted/单项结果、学习资产筛选、移动返回与目录responsive/reduced-motion等原合同约束原位保留。不是前端或REA目标采用接受。

## 1. Online reader's current-state snapshot

### 2026-10-20 Issue #17 first source repair — FIX-089

PR [#85](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/pull/85) is an open, unmerged source candidate from main `3f6d67785752b465b5b022847cbbe75a55e1eb47`; initial code head `dff5b4a4635dddfc288a5139dbbcda4039aced3d`. It addresses only `FIX-089 · LOWER_ADAPTER_CACHE_SCOPE`: `lumenis/adapters/base.py` now binds cached fallback to complete actor/scope/query/task/source-version/result-limit identity and writes result+identity atomically; `lumenis/adapters/registry.py` carries an optional keyword-only context through existing search methods. Existing callers without complete trusted context retain live searches but fail truthfully without cached fallback. The current V4 search callers have not yet been wired to an authenticated complete context; their degraded cached fallback remains unavailable until their existing caller owner closes that boundary. No W6 composition file changed.

Exact source regressions are in `tests/test_adapter_resilience.py`: `UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --no-project --with pytest python -m pytest -q tests/test_adapter_resilience.py` — 20 passed. `python -m compileall -q lumenis/adapters/base.py lumenis/adapters/registry.py tests/test_adapter_resilience.py`, `python scripts/audit_tools/verify_ai_native_constitution.py` and `git diff --check` passed locally. The first exact-head Product Gate run failed its blocking machine-governance step because the delivery commit omitted this required CURRENT co-publication; that failure is retained and this CURRENT update is the correction for the next exact-head run. Its advisory Boundary Check reported 28 existing findings; the same command on exact base `3f6d67785752b465b5b022847cbbe75a55e1eb47` reported the same 28 (not introduced by this PR). Latest-head required checks and review are still pending; neither source tests nor this record establish runtime, database, real-source or user acceptance. All other still-open Issue #17 work remains open; this first PR is not the complete repair scope.

Independent review of exact head `34ecc470e0dc276dd06737044f919c2edc4fe811` found that callers could mutate the live success result and cached notes through shared object references, including nested `raw_data`. The existing cache owner now stores a detached deep snapshot and deep-copies cached notes for every fallback; if snapshot copying is unsupported, cached fallback is unavailable rather than aliased. Regressions mutate the first live result and first fallback, inject `TypeError` during snapshot storage and reads, and verify a fresh live success clears the older cache. The registry-forwarding test now restores the process-wide singleton through `monkeypatch`. FIX-091 integration review found terminal verification errors could be downgraded to cached or custom fallback success; `_fallback_or_fail` now returns the original terminal failure before consulting any fallback. A subsequent breaker review found the open-circuit shortcut replaced the provider error with a generic breaker message. `BaseAdapter` now retains the most recent provider failure in existing adapter state; while an open breaker follows a terminal response, it returns failure with that cause and bypasses both custom and cached fallback. Regressions warm both empty and non-empty same-identity caches, issue five challenges through the configured threshold, verify the sixth call makes no provider request and remains failed, and confirm an explicitly permitted normal request after cooldown recovers. A separate regression confirms repeated ordinary transient errors still use same-identity cached fallback after the breaker opens. The isolated adapter suite passes **30 tests** with `UV_CACHE_DIR=/tmp/lumenis-uv-cache uv run --no-project --with pytest python -m pytest -q tests/test_adapter_resilience.py`; changed Python compilation and `git diff --check` pass. This closes only the cache alias, terminal/breaker-state and test-isolation paths; exact updated-head CI/review and all runtime, database, real-source, user and remaining Issue #17 outcomes remain pending/open.

Implementation publication state: `PUBLISHED_SOURCE_VERIFIED`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
Database state: `NOT_VERIFIED`
User outcome: `NOT_VERIFIED`
Real user E2E: `NOT_VERIFIED`

Candidate source publication at [PR #83](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/pull/83) was verified first at `4c95faaaaa5fb52b676d2f63166968f097e7359f` (3,947 remote blobs and modes), then the bounded CI repair was published at `57e41b4ff276f03ce9b2efe874768c5defb2d413`, tree `6a6bc9909be20b7e76b00e08e75b7d5f384d3411`. On that second head Flutter analysis and Web build passed, while Product Gate failed on 13 tracked path names. Both rounds of failures remain evidence. The follow-up increment normalized those paths byte-preservingly, repaired exact single-use approval in the trusted in-process compatibility library, closed three compatibility API authorization gaps through existing account, Task, Source and Evidence owners, addressed the four reviewed observation-replay/media-input findings, and repaired periodic fault-diagnostic frame traversal and sink lifecycle (normal process restart required; not a hot runtime repair). Its package identities and validation remain in FINAL-VALIDATION.json and FILE-HASHES.json. Merged lineage (git readback 2026-10-20): `57e41b4` and the increment `3137431` are both ancestors of merged main `3f6d677` (PR #84 merge) and of every later main; the earlier "unpublished / main `4dab98e` / merge and readback remain" statements are superseded and must not be repeated as pending work. The publication state above records this documentation-only publication. Runtime load, database state and user acceptance remain NOT_VERIFIED. Arbitrary OSAI/MCP producer SourceUse bindings and unowned historical-result migration remain open; unknown producers fail closed without deleting their product requirements or historical files.

2026-10-16文档审查原位清理 Security/Experience 的账号与两种开发者模式旧延期句，并将已批准实时语音目标对齐 Architecture/Overlay；该批未启用麦克风、模型或服务。当时AI-05和草图限于Groq固定端点，任意HTTPS执行限制尚有实现缺口；这项历史观察不代替当前源码、精确批准与执行边界核验。首个文档提交的Product Gate因三项Architecture精确措辞不匹配失败，失败记录保留；本次恢复等价的唯一Gateway/退役路径安全表述，未删减校验。

2026-10-18直接PO已批准完整19类能力及新增要求的完整开发，沿既有Owner承接同一个完整产品闭环，保留已批准的范围和排除项，不另造产品/规划/队列。当前优先完成完整候选PR整合、门禁与合并；为此安排开发先后或暂缓执行不取消已批准能力范围。当前分工：云端dot负责候选PR整合、后端/数据/AI等获批能力实现与bug修复、同版测试、日志备份及交接；本地Codex与Akang（GrokBot）仍由PO等权安排前端实际构建及必须本机完成的验证，互不取得对方派工权。云端按已批准流程将同版候选提交PR，回归、实质审阅及必需CI通过后正常合并并远端读回，不以等待本地Codex上传为前置；本地候选后补核对，原有未提交工作与真实端侧验收分别保护和保留。2026-10-16仅文档收尾的历史延期不再限制这次已获准开发；本记录不自动启动其他窗口、不派工Brio、不改变模型/额度，不越过既有前端、Permission、数据与发布边界；完整开发批准不代替具体外部模型调用、训练、费用、生产写入或上线部署所需的原适用权限。唯一完整前后端规划为 [product-plan-full.md](LOOP-PLAN-20261014/product-plan-full.md)，唯一完整视觉文字草图为 [FULL-PRODUCT-SKETCH.md](LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)，二者覆盖今天更新及全部既有 SYSTEM/CTH/BMP/Shared/Agent–自研 AI、四表面、195 个 G 和原 J/R/U；44 屏只是追溯基线。Architecture、Experience、Owner、验收规范、逐屏合同各保留唯一内容责任，README只作稳定中英产品指南，不复制状态。

| 历史证据层 | 2026-10-16 当次收尾的事实与未完边界（不作为当前派工或运行状态） |
| --- | --- |
| 已发布源码与文档 | PR60/77/78/80 的既有回执按原版本保留；本次开始读回 main 为 `0907fd67f71500bd3065485d873a3324d0efbda5`。本 PR 只发布13条现有文档路径和原治理检查器的一处过时账号句匹配，发布结果以本PR合并提交和远端读回为准，不复制未来SHA。 |
| 完整规划与前端 | 完整前后端计划、全产品视觉/操作草图、研究直传和逐材料分析时间线/物理卡片、产品语言、四端、账号/两开发者模式等已纳入本次文档；**整体前端 NOT_ACCEPTED**，这些仍须真实实现与验收，不能以局部文案/编译/规划当通过。 |
| 受保护主工作区 | `akang/auto-scope-all-subjects` HEAD `7792040e1251b8bf765aefb8465e1d437f65a812`，原22 tracked dirty＋6 untracked候选保留；已核19项与main一致、5项语义采用、4项无效生成物删除未采用，原文件未清理。它不是当前main或已升级Runtime。 |
| 本轮产品候选 | `codex/20261016-sourcebrief-analysis` 基于 `2932b725039ad606d9f335f8e900d989fd876182`，68条有实际差异/新源码路径冻结为 LOCAL_CANDIDATE_NOT_ACCEPTED。完整原字节/patch归档 `product-candidates-freeze-20261016.zip` SHA256 `84db066dc2034839b8923dc32414e5a823e2e629d28991f807fcaf151283d3ca`；归档是恢复证据，不是第二实现。没有将未验收代码混入本次文档PR。 |
| 候选静态证据 | 当前27条生产Python语法和Ruff F821/F822/F823/E9通过，11条Dart analyze通过；38条源码hash检查前后相同。`freeze-source-validation.json` SHA256 `abb9950a33ef35f88e4238769ace949945d84682649d6fe47e5daf22f005be80`；完整Ruff/全组合回归/构建/用户E2E未由这次冻结执行，历史失败及SH02旧hash差异归因UNKNOWN保留。 |
| Hooks PR79 | 推送头 `e162b71b9c7715e1e2c8a9eda48c9e84faa3f51a` 的 Product/App CI成功；四条新增P1（同文新PO turn、Stop续接来源、ignored owned路径、pending effect admission pins）仍OPEN，不能合并/激活或称全部修好。本次不继续工具代码实现。 |
| Runtime / Database | 原生产8201未在本次重启/升级；隔离58577的最后启动回执为PID16652、boot `3b6b8a6bdf614fec86245044e373fb3f`，无Scheduler、隔离DB。当前存活/装载组合不因历史启动或文档推断。首次真实导入confirm503、未持久化独立读回/预览过期保留；最新源下五文件完整用户导入与成果链 NOT_VERIFIED，不自动重放。 |
| 采集与主体 | 注册、获准自动采集补全、Source/Evidence/Canonical或Pending、刷新/恢复和下游用户成果全部保留。最新维护任务观察为Disabled、PT5M/Logon；237旧计划保护性迁移仅为候选，未执行生产迁移或恢复调度。受限身份只阻塞自身，手动导入/静态通过不能证明自主采集已闭环。 |
| Groq / 自研AI / REA | Groq是唯一获准外部接口，显式选择并经现有Gateway/Permission；源码host allowlist与调用权限仍须真实闭环，不能将当前任意HTTPS适配能力当授权。自研训练/checkpoint重载/独立评价、Hybrid交叉精排、Math完整适用算法和模型收益各自待验。REA V2完整输入已保护，31条离线资料未准入；采集/办公/媒体/平台底层方法和UI采用须接真实Owner与用户链，不能用包/截图代替。 |

2026-10-19 现行纠偏（来源：用户当日06:43 UTC（北京时间14:43）澄清“我规划的是唯一接口，可以接外面任意key，这个只是我给产品内置的”）：上表记录当时有界执行范围，不构成永久BYOK供应商限制。当前完整目标是唯一SYSTEM Gateway、产品内置Groq、用户自带其他供应商API及自有模型建设目标；对应协议、安全目的地、凭据隔离、Permission/SourceUse与实际用户成果仍分别验证，不自动启用凭据、调用模型或恢复退休专用路线。

五份附件已完整只读解析及校准：三份XLSX共11sheet、820物理行（813非空，811条非表头投影）；PDF2页36块；DOCX198段落对象/143非空。102清单与最终表交集79个ID，23/44各自独有；最终129行仅123个唯一可识别ID，不能与85/102样本相加。85行中58无链接/日期、49标题/作者占位；最终表9个明示日期越出报告时间窗。322评论中36无父帖编号，286数字编号有147一致、138标题冲突、1无父帖。来源报告的情感标签、约40强相关、“零缺口”等保留为来源主张，不推广为事实、代表性比例或因果。证据 `source-materials-review-20261016/source-materials-review.json` SHA256 `0a0549d3d6d08df745423fcce49aa2dea66d6020963d066738d93aa7251120ce`；定位复核 `importer-five-material-locator-replay-final-20261016.json` SHA256 `b3b091d1da6c9d62143a28ced37e6816120569ec03b4efa9bfd1559043cee144`。原件留在受保护本机，不提交到Git。当前候选已补全表投影/原件保存与PDF/DOCX定位hash等，普通直传/自动逐材料分析/物理卡片、跨域接线和完整保存恢复在该批仍待实现验收；当前按§1接续，不以旧停点延期已批准工作。

所有未完要求统一留在原完整计划和本机既有 `full-resume.json#continuity`：#17/Slack逐项采用和Brio/历史PDF/Cortech原报告完整研究、Cortech19类非Muse账号功能、REA真实采集/资料/办公/媒体/Agent方法、Math/Hybrid与独立训练、主体/采集、自有素材与跨域SourceUse、持久聊天032/048、Pattern045/FactWall046、54bindings/11chapters、制作/来源撤回/崩溃恢复、全前端及四端真实用户结果、候选安全集成、精确组合版本CI/运行/数据库/发布。原研究/失败证据不删；上述任何项未完成都不能将同一产品闭环记为完成。

本机精确证据根为 `C:/Users/private-user-121dcc385158/Documents/Codex/2026-10-16/issue17-repair/`，只作同一任务的恢复/验证材料，非另一规划权威。历史136 source rows→122去重消息、33评论/43频道消息/7线程53回复的核对在 `history-reconciliation.json`（SHA256 `67ca2f94a9da35685f2ef499285257f123a9039bc6364dddc91f63212780dc72`）；逐source处置为 `issue17-slack-deduplicated-disposition.md`（`d7fac655f54dfda392cc34e4c6b3faabb2ddd861b472fcdd4927daa98f90f792`）。这些明确采样的消息读完不等于附件全文研究或产品采用全部完成。

本次规则校验先发现根指令字节预算超限及检查器仍强求旧账号后置句；已压缩重复路由说明、保留唯一规划链接，并让原检查器明确核验已批准的账号/免费登录/双开发者模式在工程闭环内、Apple准入和无通用账号墙/Permission，不删检查、不改机器合同或放宽门禁。首轮失败保留，最终结果以当前版本检查为准。

以下保留既有各批次原始范围和失败/未完结论；不把其旧回执自动迁移到本次组合版本。

前述工程钩子发布批次仅包含 M 的既有工程钩子、受影响回归和规则说明；该批不包含产品行为源码，不升级下述已发布产品回执的验收范围。原生注册与受保护主树中的实际钩子装载须在合并后独立读回。

本次 PR #60 冲突收敛保留当前账号/免费登录、独立工作区、视觉和来源同权规则。规划继续只使用 `00-GOVERNANCE/LOOP-PLAN-20261014/` 的现行版本及 [唯一完整前端规划](LOOP-PLAN-20261014/product-plan-full.md)与[唯一视觉文字草图](LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)；不恢复旧目录下的重复规划。补入既有 Gibbs 训练/validation/holdout 三份原始日志并链接当前数学采用记录，状态仍为“已训练、未上线”，G163 仍 OPEN。这是规则与历史证据同步，不含新训练、产品运行或验收升级；下述 PR #77/#78 回执保留其原有范围。

本批承接 Issue #17 正文及 33 条评论、#lumenis-dev 43 条频道消息及 7 个回复串的 53 条回复，共 136 条来源记录、122 条去重消息；逐条读取、映射并保留全部未闭项。Brio 两个新附件包的 10 份文档已读并映射；历史四份长 PDF 的既有部分阅读边界保留，消息全覆盖不等于全部研究材料读完。本批修复 KOS 三处未定义服务调用、AI 状态把分析模块导入误报为模型可用、Shared SavedWork 的独立工作区 Scope，以及视频工程因任意转场而全面禁用编辑的问题。独立 Shared 容器不继承 CTH/BMP 权限；所引用来源仍逐条保留原 Scope、SourceUse 与权益核验。媒体编辑按实际 Core 转场约束原子拒绝无效修改，保留撤销和版本，不用删除转场换取表面成功。当前前端规划和逐屏参考原位补齐完整任务、独立制作、返回/保存/恢复和四表面差异；44 个历史屏号不是范围上限，文档更新不证明实际界面已通过。

同一修复源码与 Web 构建在隔离本机 Runtime 实际完成独立 Shared 报告的人工输入、v1 保存、v2 修订、旧版重开、页面刷新后新版重开及 Markdown 下载，下载正文与修订内容逐字相符；不调用 AI、不写生产 DB。媒体导入确认保留单次用途和稳定 Artifact 身份，SQLite 主键及独立尝试文件避免并发覆盖。跨 CTH/BMP 素材到 Shared 的正向用途确认、多 worker 确认状态路由、完整媒体 UI、进程崩溃恢复和四表面验收仍 OPEN；隔离报告链通过不升级这些结果。Cortech 的可取得第一方源码已审计，19 项能力意图映射既有 Owner，排除 Muse 产品账号实现；可编辑前端原始工程缺失和第三方许可缺口保持明确，未整体移植或运行 Cortech。

Groq 仅使用已有显式选择的 `user_api` Gateway；不启用 Gemini，不自动回退。状态读取保持配置与运行分离，不探测或调用模型。旧通用数据/学习调用不会因全局 API 配置而自动外发；当前允许的无业务库用户对话显式声明输入类别，传输前复用既有脱敏。已在隔离集成源码通过一次获准的无业务数据 Groq 实际响应核验；其回执不证明当前 8201 Core 已加载本批，也不代表 AI-01 全任务、业务分析、训练或自研模型完成。保护主工作区 `akang/auto-scope-all-subjects`、原候选和运行服务；当前运行与本批源码的组合一致性、生产 DB 和完整用户 E2E 仍为 `NOT_VERIFIED`。详见 [同批 round-15 修复回执](evidence/round-15/ISSUE17-SLACK-PRODUCT-REPAIRS-20261016.json)；未闭项保留，不以源码或 CI 通过清零。

同批后续修复关闭 app.py 六处未定义名称，并让兼容运行状态接口委托实际聚合 Owner，读取启动器使用的 app_main Guardian。历史租约、心跳和检查点仅记录 OBSERVED；未知不补零，不伪造 ACTIVE 或执行时间。运行诊断沿现有认证，worker 只返回原有四项概要字段；快速安全扫描缺失或失败明确返回不可用/错误。13 项隔离回归、三文件编译和关键 Ruff 检查通过；真实聚合接口及临时数据库观察到清理器停止→运行→停止。既有安全 Core 配置对该诊断请求的 403 保留，未扩大 allowlist；组件读回不代表完整 Core/用户 E2E。全文件既有 Ruff 问题、生产运行同版装载和全产品未闭项保留；原工作区 28 项候选未变，生产 8201 未重启，Hook 未关闭或放宽。

通用CTH风险策略v2.1不再因参考主体名称命中而加分；商业风险词、升级规则、阈值及未知值语义保留。Gateway兼容审阅缺精确主体投影时保留规则结果并明确增强未就绪，不猜主体；有投影时显式传递名称/别名，形状校验不替代上游权限与来源证明。历史风险评分不回写，其未记录的策略版本返回未知，当前计算策略另列。77项隔离回归通过，正常产品运行、数据库与用户结果尚未验证。

退役Provider残留继续在原Owner收敛：删除旧HTTP探测和按次计费执行体，兼容入口只返回不可用；历史额度/使用记录保留。标准AI目录采用中性路径，显式配置保持，不移动旧文件、不启动服务。隔离回归/静态通过不等于运行或用户验收。

显式选择 user_api 的已有通用接口保留；状态读取不调用外部模型、不探测端点，配置完成仍为 CONFIGURED_NOT_VERIFIED，不能冒称可用或自动切回 owned。

本批修复缺失风险/日报数据的数值语义：缺失返回None，真实观测零值保留；报告、摘要、行动和导出调用方检查未知值，不误报正常或品牌健康50分。保留原评分范围和实际业务权重。编译、静态和隔离回归仅证明有界代码；当前Runtime未加载、真实日报用户验收未进行。规则/逐屏草图/隧道分别PR #61/#63/#62已发布；其他类别仍独立验收。未操作原有工作分支、Production DB、模型或运行服务。已合入PR #64的Gateway清理及Gibbs回执：已训练、未上线，G163仍OPEN；本批不重复训练或声明模型收益。Gateway状态接口和Agent观察读取CTH/BMP实际服务绑定，汇总逐域状态，不把评估候选当运行服务；用户已选API只显示配置未验证，不发请求、不回退。历史退役Provider媒体评价通过原Evaluation读接口、汇总和AI面板统一标为HISTORICAL_NOT_REVERIFIED，保留原记录/快照，历史PASS不计当前通过。运行时加载及真实用户验收仍未验证。

PR #66已发布：采集脚本不再默认参考主体Profile或固定CDP示例；账户Owner核验获准的HK/intl身份及Profile，JS拒绝任意Profile、目录逃逸、错误身份和不安全Cookie域/URL；远端CDP复用已注册worker身份，不复制本机Cookie；独立脚本导航和响应仅认国际RedNote。ACC-02继续GLOBAL默认，参考主体仅作深度覆盖；历史资料与失败证据保留。隔离检查未读真实凭据，Runtime与用户采集验收仍为NOT_VERIFIED。

PR #75（源码提交`586776b3b1a94d143cc88cc12bcd825f248b8ee5`；当前远端PR分支含合入fresh main的组合版本）在既有SYSTEM Browser/Collector会话链补齐动态注册worker端点、进程/内核/Profile与身份核验，人工接管actor/task/lease传递及切换后端点重解析，并为搜索页提供任务级清理；采集后分析仅使用持久化Query Plan的服务端scope，没有可验证Scoped Evidence的旧事件阶段明确阻断。隔离回归114项Python、13项Node通过，变更Python编译、Node语法、constitution校验和CRLF-aware diff检查通过；所选路径Ruff仍有842条存量诊断，新增行无诊断。本轮审查修复补齐子进程精确service Python与Profile断言、跨平台Edge发现、Playwright受支持的连接释放、品牌重新启用的真实未采集状态；Google/Zhihu使用各自已登记后台worker，身份/挑战/连接失败不通过替代路径绕过。人工登录增加同actor/task取消及15分钟过期检查（状态/保存/取消/下一次显式登录触发），即使原任务核验状态已变化，返回操作仍须同actor/task已持租约及Browser Permission；只有核实返回后台才释放既有租约。新增该生命周期回归9项通过；无法证明重启后会话归属时拒绝猜测，自动孤儿接管恢复仍OPEN。增量15项Python与15项Node通过，编译/JS语法/差异通过，Ruff逐文件与HEAD对照无新增而非全量通过。PR #76 已合并至main（451d70eac6fdf510d6f9851eff8ea8415a50fcc7），本批普通合并该版本后复核Query Plan → 精确Scope → 分析/事件API组合，未复用不匹配版本的验收。同步搜索子进程也强制继承当前服务的绝对Python解释器并覆盖外部继承值；动态端点操作保留已验证账号，通用浏览器控制仅消费BACKGROUND，人工登录仍经专用actor/task/lease路径。Google使用既有注册机制的独立Profile，不连接个人端口。新增身份回归拒绝缺失或不匹配指纹，不弱化持久化身份保护。页面观察复用既有只读提取器，正文在页面侧限制2000字符、DOM保留400节点上限与真实截断状态，修复未定义表达式。该最终组合15份相关回归共243项通过、0失败/错误/跳过；15项Node身份回归通过，40个改动Python文件编译及JS语法通过，13个最终路径所选E9/F63/F7/F82检查通过（不是全量Ruff通过），架构/治理/constitution门禁及差异检查通过。旧夹具失败回执保留；修正只对齐真实注册Owner、身份、参数和来源页面，未删除正向/拒绝/UNKNOWN断言。SOURCE经本PR及精确CI发布；源码发布不升级运行结论。Runtime、DB、真实浏览器/会话、定时采集和完整保存/重开/恢复用户结果均为`NOT_VERIFIED`。

本批通用业务搜索、分析、报告与导出不再隐式选择Subject/BrandFocus；业务读取沿服务端认证Scope，并逐条核验Canonical/Evidence/SourceUse。摘要截断、来源拒绝和覆盖不完整保留UNKNOWN/不完整，真实零值不变；`web_mention`与note进入同一统计链，不按来源类别改变权重。`/api/export/generate`保留JSON响应合同并复用SavedWork生成、读回；已保存报告下载在释放文件前重新核验保存时的来源绑定与当前SourceUse，并保留DATA_EXPORT；无归属旧平面文件不开放任意下载。AIHub与仍注册的`/api/ai/chat`兼容入口均只把静态功能元数据用于路由提示，普通聊天默认经现有Owned Gateway；用户明确选配user_api时，仅无业务库用户对话可显式调用该接口，未绑定逐来源SourceUse时不读取或外发品牌目录、案例、业务统计或Canonical日报。日报缺失的负面数量和情感保持UNKNOWN，不回退到风险事件数或合成中性。焦点报告保留daily/weekly/monthly/yearly。GLOBAL目前仅有精确日报支持；旧ReportGenerator与engine没有可复用的已授权GLOBAL多周期路径，周/月/年仍为NOT_VERIFIED并明确不可用，不以默认主体代替。此前31条代码与回归路径的Git blob清单SHA-256为`e84e2d2e674374cda4d46372e543cc6192d88e0c3a1d98791e31c12555422935`；该指纹只覆盖此前有界子批，不包含本次最终Permission/Reporting路由修复。

定向回归196项通过、2项跳过；跳过的是既有导入器覆盖：`:920` 的XLS二进制解析要求可选 `xlrd` 与本机 `soffice`，`:951` 的旧DOC解析需要本机LibreOffice/`soffice`，与本批报告导出格式改动无关。31个改动Python文件编译通过。七个直接相关路径的所选Ruff规则为111项既有诊断，与同口径origin基线133项相比无新增；这是增量对照，不是全仓Ruff通过。`git diff --check`通过。Gateway源码复核通过；Runtime加载、生产DB和真实用户E2E仍NOT_VERIFIED，本批未操作它们。PR #76 的最终路由修复涉及 `app.py`、`lumenis/shared/reporting/routes.py`、`lumenis/system/security/permission.py` 与 `tests/test_reporting_route.py`：认证请求Scope解析归入SYSTEM Permission，`app.py`仅保留兼容包装，Shared Reporting直接调用该Owner。受影响路由回归8项、单产品架构守卫、Python编译与差异检查通过。PR审查发现的调用缺口已在原Owner修正：事件审核接收服务端签发的本地工作区身份；报告核验先按请求时间过滤；完整样本空日为真实0，未知覆盖或分类保持None；截断来源在事件持久化前返回PARTIAL并保留既有完整事件；采集后处理按每个已准入精确Scope独立分析/聚合，含糊关键词不猜主体；作者检索在已核Canonical来源内先按作者过滤再限量；canonical报告与Word/PDF导出沿相同Scope、SourceUse和DATA_EXPORT边界。最终组合的17个受影响回归函数（参数化后20项）通过，16个改动Python文件编译通过，架构和Database唯一Owner守卫通过；E9/F63/F7/F82静态检查仍有app的6项和KOS的3项既有诊断，与HEAD同口径结果相同，没有新增，不能报告全量Ruff通过。Word/PDF部分写入失败只清理本次唯一文件，保留已成功格式；导出保留用户日期。追加审查修复：CTH-04/08、BMP-10传递服务端核验Scope，读失败不伪为空；dashboard各业务聚合统一消费同一Scoped Canonical/Evidence样本，截断或未知时间不填零；关联笔记已知高风险分数优先；full_refresh写入前必须取得既有Shared数据库快照，失败时所有写阶段NOT_RUN；日报只分析已核相关记录，相关性不完整时保留UNKNOWN。ACT建议移除固定主体与退役Provider，保留可编辑确定性建议，AI增强绑定仍OPEN/UNAVAILABLE，不宣称已执行动作。该组合4份受影响回归共46项通过、10个Python文件编译通过；所选静态规则仍有app.py六项未变化的既有诊断，非全量Ruff通过。事件分组达到上限时保留PARTIAL及已处理/剩余数，full_refresh传播该结果；KOS使用Permission回执中的真实actor或本地工作区caller，审核动作绑定实际展示的suggested_reply，缺文本拒绝登记；作者未知或互动不完整/零分母不生成假归因百分比。这六项审查修复的隔离KOS定向29项、事件/刷新定向5项通过，目标Python编译通过；ACT入口另拒绝非对象、错误字段类型及纯空白问题，页面/ACT回归11项和该路径所选Ruff规则通过；新回归文件末尾空行已规范化，差异检查通过；遗留源码Ruff存量问题仍单独保留。此前回执只适用未变化范围，不自动成为当前组合验收。Runtime加载、生产DB与真实用户E2E仍NOT_VERIFIED。

本文件呈现当前有效的交接入口和未闭要求；既有日期事实只作版本化证据，不成为旧指令或当前运行/完成声明。线上与本地研发读取同一套有效规则，云端dot按§1的2026-10-18直接PO分工接续。此前规则清理未包含dot接续的范围记录已被本次明确授权更新；不启动Brio产品开发，不修改用户管理的F/M原生Goal。

本次修改范围：移除经全文核对的退役执行正文、嵌套副本与活动引用，包含旧ZBC/OSAI执行基线及双仓库硬门；有效安全、复用、资料采用与验收要求由原AGENTS/Architecture/Experience/Owner承接。原缺口清单及绑定镜像纠正CTH-09已有Decision Owner与Flutter reader却标ABSENT的失真，并纠正已见Widget和Shell入口的屏幕不存在声明；汇总由同一批原记录计算。44份实际屏幕规范中的全局二维/禁3D旧限制已在原段纠正，未以模板更新代替消费者修正。屏幕存在、字段接线、动作、权限和用户验收分开，PENDING不改成通过，其余源码/运行语义不由存在性检查升级。 旧蓝图55章中的有效差异/置信度/配置管理/服务与采集诊断/格式失败边界已回填原Owner职责，旧Provider配方与示例值不恢复；这是要求承接而非11个新项目或实现完成。Shared目录仅按当前架构和真实Python绑定读取。原源码、未完成候选、研究原件、审批、业务数据与失败结果不因清理规则删除。

此前发布（规则-14，阿康（bot））采集先免费广告/流量与创作者中心数据、聚光延后；创作须 Brief/人设模板/调性/事实质检；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。上一发布（PR #40 AI-01 可信范围，阿康1（bot））：AI-01 提交只认服务端 FOCUS 范围的产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前发布（PR SH-06 收件箱，阿康1（bot））：SH-06 只读收件箱后端产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前发布（PR AI-01 回执，阿康1（bot））：AI-01 提交回执校验产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前发布（PR #35，阿康1（bot））为 SYS-06 内置浏览器实时画面流产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前规则型发布：AGENTS.md 固定 LF 换行（内容不变），T04 历史禁止项迁入机器合同 red_lines，由阻塞校验器结构化检查；不含产品源码。此前AGENTS.md LF/T04发布仅涉及治理文件，不代表产品源码已发布、生产已加载或用户任务已验收。下段 PR #25 主体登记源码已按源码口径发布。

此前主体登记种子发布包含产品源码：`scripts/import_subject_registry_seed.py`（默认 dry-run；研发阶段由开发者备份数据库后直接执行 `--apply`（PO 2026-10-13 直接指令），且只经既有 `subject_registry.add_subject` 幂等写入）与已在线核实的种子 `scripts/data_candidates/subject_registry_seed_20261013.jsonl`（610条，清单固定sha256），并登记全球数据源研究现行版；场内 TENANT_OF 关系仍为候选、未写入。`PUBLISHED_SOURCE_VERIFIED`不代表生产已加载、种子已写入生产库、真实用户任务验收或产品功能完成。此前 AGENTS.md 重复叙述精简（PR #26）与 T04 历史禁止项锚点（PR #24）按规则型发布，第7节复用诊断源码已由 PR #23 按源码口径发布；结果以实际Git对象和Actions核实，不在文档中冻结“当前main”的SHA。

本轮在现有规则型提交的精确文件白名单内，原位降级四份存活旧执行语义：历史 ADR、两份内容制作母指令与 AI 编程旧基线，均只保留归档研究身份；有效 J6/C4 的 Daily/Weekly/Monthly 播客选题与可编辑成品要求已在现有 Owner 保留。此项来源清理不等于开发、运行或产品验收完成。

2026-10-13 REA 媒体/办公接入（PO 授权逐段合并）：把 `D:/REA-Review/2026-10-11/product-patch` 的12个文件补丁在当前 main 上逐段接入原 Owner——C4/C6 `shared_artifacts.py`/`experience_runtime.py` 与 SH-01 正常制作不再要求 demo 勾选（旧参数仅可选兼容，`rights=unknown` 不升级）；C5 `lumenis/shared/reporting/saved_work.py` 增加 DOCX/XLSX/PPTX 精确 OOXML 校验与回读；F `app/lib/features/shared/sh01` 视频/播客共用 Timeline。FFmpeg 继续由 `LUMENIS_FFMPEG_PATH`/`LUMENIS_FFPROBE_PATH` 配置，不硬编码研究目录；REA 适配 wheel 未作为产品依赖。运行加载与真实用户验收仍为 NOT_VERIFIED。

2026-10-13 广州太古汇场内分布入库（PO 批准 PO-20261013-TKH-DIRECTORY-INGEST，原话：“这个表格是最新的，最准的，直接入库，然后数据源闭环，闭环前这些数据就ok，以后就只是新增主体，官网没更新”）：新增来源类别 `PO_PROVIDED_AUTHORITATIVE`，PO 提供的文件以 sha256 固定、以 `po-provided://` URI 标识、清单记录批准号；经既有采集持久化 Owner 写一条来源笔记、既有 Evidence Owner 签名、`persist_existing_note_scope` 绑定精确 CTH 场所范围后，才由 `record_venue_tenant_claim` 写 TENANT_OF（一律 UNREVIEWED）。`scripts/import_tkh_directory_relations.py` 与 `scripts/import_subject_registry_seed.py --seed tkh`（137个新 BMP 品牌）均默认 dry-run，`--apply` 须经 PermissionGate 精确人工审批；种子导入新增同名异体保护（英文或中文单边同名即暂缓，不建近似重复）。文华东方（MOH）铺位及酒店餐饮/水疗不属商场铺位，不写入。顺带修复 `persist_social_note` 25列/24占位符缺陷。闭环前数据源规则：闭环前数据源 = PR #25 的610条主体种子 + 本场内分布；闭环后只做新增主体，不替换既有基线。生产库写入与用户验收另行取证。

运行与结果：RUNTIME、DATABASE、USER OUTCOME均须独立取证。未取得本轮证据时标记NOT_VERIFIED，不复制旧进程、端口、账号状态、测试数、模型状态或历史PASS。

## 2. 唯一有效入口 — CURRENT CONFIGURATION / TOOLCHAIN CONVERGENCE

| 事项 | 原有权威位置 |
|---|---|
| 仓库执行路由 | `AGENTS.md` |
| 产品原则 | [The Product Owner's lightweight AI-native constitution](AI-NATIVE-PRODUCT-CONSTITUTION.md) |
| 配置示例 | `.env.example` is documentation only；不以示例覆盖实例私有配置。 |
| Flutter工具链 | `app/toolchain.json`与已有依赖锁文件为实际构建输入，不在接续文档复制版本常量。 |
| C2实例配置 | local private C2 runtime specification 保持实例私有，加载/权利/权限依据实际读取，不能由文档推定已部署。 |
| 机器治理语义 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json` |
| 产品范围与五轮交付 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` |
| 用户体验与四表面 | `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` |
| 完整源码职责和R/J/U要求 | `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` |
| 真实成果与退出条件 | `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md` |
| 主体、范围、来源和数据成熟度 | `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` |
| 来源返回合同 | `contracts/experience/source-target-contract-v1.json` |
| 跨仓约定 | `00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md`、`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json` |
| 任务与协作索引 | 本仓库Issue #17及其原任务/PR，不构成第二套产品规则 |

跨仓机器合同固定协议指纹：`68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`。协议版本标识不同于实时产品版本。

当前明确PO要求确定目标与授权，源码/运行证据说明已经实现和证明了什么；不能用缺少实现取消需求。规则冲突在原权威位置修正，不把冲突双方一起复制到本文件。

## 3. Current owner continuation

以下是职责与未闭验收，不是窗口开停、模型配置或执行中的状态表。2026-10-18云端dot与本地Codex/Akang的当前授权分工见§1；仍复用本表原Owner，不新增人员层级或改派Brio。具体目标以Source Owner Index的原完整成果卡为准；需要执行时读取原任务的当前准入和最后有效回执。

| 原源码职责 | 完整工作与待核结果 |
|---|---|
| C1 / W1 | 主体/品牌/关系、原生采集、来源时间与字段、Source/Evidence/Canonical、持续供料和恢复；按真实任务范围、合法会话和原权限验证，不用来源数量代表覆盖。 |
| C2 / W2 | 当前Owned Gateway、Agent任务、上下文、取消/恢复、评价与受控学习；与C5完成cosine/BM25/融合/cross-encoder完整合同，训练、模型绑定、重载、语义质量和晋升各自验收。 |
| C3 / W3 | CTH/BMP完整问题驱动分析与业务对象、可用判断、获准动作及真实结果；基础业务无AI运行，来源/预算变化、保存、修订、重开和恢复必须连续。 |
| C4 / W4 | 独立提案/文稿、视频、播客的完整编辑与交付；保留用户原稿、原素材、方法、项目版本、实际媒体输出、回读、视听检查和恢复，计划不替代成品。 |
| C5 / W5 | 资料原件、检索、引用、SavedWork、报告/导出、版本、通知与Shared独立工作空间；现行来源用途和对象权限贯穿所有入口，复用已有底座。 |
| C6 / W6 | 同版本集成、Core与依赖、运行身份、数据库迁移/恢复、打包、各端真实操作与发布；保护其他候选，分清Change、Owner Closure和Release。 |
| F | 官网、Web、Windows/macOS与iOS按各自角色并行建设、独立验收；完整任务交互、三语、无障碍、原研究采用和真实成果接续，不以页面数或视觉草图结项。 |
| M | 当前授权范围内的跨Owner协调、源码判断、整合与最终工程验收；不凭本文件自动启动/暂停其他Agent，不重建用户管理的原生Goal。 |

## 4. 必须带入接续的完整要求

- 产品按SYSTEM、CTH、BMP、Shared、Agent Groups/自研AI五轮组织完整交付。工程职责不是额外轮次；当前任务依赖不得推给后轮。独立Shared研究、文稿/提案、视频和播客不要求先建立CTH/BMP主体、任务或SourceBrief。
- 四表面依角色并行，不让一端未完成暂停其他端独立工作。Windows/macOS和iOS是原生目标；Linux服务、CI与浏览器工作不因原生目标而受限。44份屏幕规范是能力覆盖，不是页面上限。
- AI横向增强既有领域，保留聊天；基础业务、确定性分析、人工创作、保存和恢复不依赖模型/API/GPU。数学方法在原后端Owner适用执行，普通用户输入真实问题与约束，不被要求组装内部算法或ID。
- Hybrid要求保留余弦向量召回、BM25、融合及真实cross-encoder重排。配置或论文记录不能证明已接通；精确模型、数据、权利、资源和授权按现有合同核验。
- 彩绘用于图标及适合的局部元素，整体空间、层级、动效与交互按原批准研究和真实任务设计；不把全产品收窄为二维水彩/纸感，也不统一为3D或卡片模板。研究原件、逐帧/页面范围、采用结论与对应实现不得遗漏。
- 数据按主体/品牌/任务和明确时间窗处理，各来源类别等权不等于每条证据同可信。原生时间、正文、封面、作者、链接、缺失和真实零值分别保留；来源引用不替代事实验证或行动授权。
- 平台账号、来源用途和训练/发布权利按原授权逐项核实。不得因为开发、审计或资料共享授权就自动开展账号操作、采集、模型调用、训练、付费、生产写入或部署。
- 所有R01–R15、J1–J8、U01–U25及未撤回的研究/素材采用要求留在原Owner合同，移除旧规则文件不撤销其中仍有效的用户能力要求。历史证据通过原证据和Git历史追溯，不重新成为执行正文。

## 5. 版本与保护边界

操作前记录当前时间、实际项目根、本地HEAD、分支、origin/main、独立GitHub main、divergence和dirty。分别使用`git rev-parse HEAD`、`git rev-parse origin/main`和`git rev-list --left-right --count HEAD...origin/main`核对本地提交、已获取远端引用及分歧，并区分其与本地未提交候选、运行进程身份。不得以固定旧SHA、旧窗口状态或已有截图代替本轮取证。

在原分支/任务中保留已完成成果、失败、未完步骤和精确输入版本。共享候选只证明他方可见；未提交代码与仅本机研究不等于不存在。按原资料权限提供必要内容，不整包公开Cookie、密钥、生产数据库或私人会话。

受保护流程为开发分支、针对性验证、独立实质审阅、必需CI、PR合并和合并版读回。GitHub同账号下不同工具的署名评论可以记录真实交叉审阅，但不能冒充两个审批身份。测试/CI通过不代替真实用户结果或整个产品闭环。

## 6. 本次完成边界

本次已核规则删除及原入口修复，必须通过原治理门、退役文件重现拒绝回归、当前Shared目录引用和线上线下字节/删除状态核对。旧工作树、仓库外规则副本、活跃会话注入与应用端缓存尚未独立核实前，不能由这批根目录清理宣称整个研发环境全部清空。

不创建旧规则备份目录或替代权威文件，不自动删除承载独有未提交代码、研究材料或活跃进程的工作树。先判断独有内容和消费者，再清理对应旧规则入口；不以加“历史”标签冒充已移除。

## 7. 独立复用接入

- 抖音响应结构诊断与可选静态DLL导入观察：源码来自 `codex/reuse-diagnostics-20261013`（`72db140a`），经 PR #23 发布，按用户直接批准的复用ZIP有界接入，不从ZIP重新覆盖；原生指标、风控失败、来源和权限语义保留，无新增采集器、数据真相、模型或运行依赖；值隔离，失败恢复沿原适配器合同。
- 现有证据为隔离工程回归（本地82项、隔离main候选59项适配器回归、各5+5项构建辅助回归），不是实际采集、新版本App构建、加载运行或真实用户验收；这些仍须各自核验。精确输入、哈希、失败恢复与未闭项见 [本批原位证据](evidence/round-15/REUSE-DIAGNOSTICS-20261013.md)。

## 2026-10-18 Python runtime compatibility and approved integration continuation

PR83 head `5160f638755c16b50c0fb84aa3317072175c9cd4` / tree `dcebff505d8879eeab8793d0e3289226cc9fca63` was read back with all 3,955 file blobs and modes matching the frozen candidate. Its App Gate passed; Product Gate passed static/architecture/compilation checks but failed dependency installation because the unchanged CI uses Python 3.11 while SciPy 1.18.1 requires 3.12. The local compatibility repair preserves the original 3.12 scientific pin, selects the official 1.17.1 pin for 3.11, and corrects two stale test fixtures without lowering production authorization or changing CI. Real isolated 3.11 validation passed 603 primary CI cases and 318 separate unittest subtests, plus 258 separate supplementary cases. See the exact scoped receipt in `evidence/round-15/bugfix-review-20261018/PYTHON-COMPAT-VALIDATION.json`; counts from different stages are not additive. This local increment still requires new-head remote checks.

The Product Owner has additionally approved full global-growth-intelligence capability and four-product protocol absorption into LUMENIS in this same main delivery, including sanitized source/document publication. Existing candidate work and requirements remain intact. Follow current LUMENIS naming, directories, Owners, Source/Evidence/Permission and truth boundaries; reconcile earlier independent-product wording to this new direction without importing duplicate runtime/account/database stacks or automatically treating research as production fact. GGI absorption is in progress, not yet implemented or accepted by this continuation receipt. The current PR must not be merged as a substitute for completing the newly included integration scope.

### 2026-10-18 研究采用交接

采用范围、唯一Owner与完整逐文件/逐API/逐能力来源由[LUMENIS-SOURCE-ADOPTION-V1.json](LUMENIS-SOURCE-ADOPTION-V1.json)链接；同一完整规划与草图、原ScreenSpec已补接研究用户旅程。A/B/C后端已交付有界源码与隔离真实session/HTTP证据，最终合并门禁待root核验；F本地实际构建/四表面验收NOT_VERIFIED；任何后续实证只更新对应范围，不能据治理回归宣称产品完成。先核当前源码与调用、再接原接口，保全部旧成果和历史失败。外仓1.1.0/原指纹未改，不把本地附件冒称四仓共同发布。不得以旧候选合并代替本次新增范围闭环。
