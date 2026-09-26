# ROUND 12 / 13 — ad metric missing-value truth

Sol decision: `PASS FOR BOUNDED BATCH / ROUND EXITS NOT ACCEPTED`. The existing read-only `AdAnalytics` analyzer now distinguishes absent spend, revenue and funnel stages from observed zero. It returns `unavailable` or `partial` instead of computing invented zero ROAS or giving optimization advice from incomplete funnel data. Existing creative analysis remains intact. No production caller, authorized ad account, user-visible result or real campaign outcome was added by this Batch.

## Exact source and verification

- Base: fetched local `main` / `origin/main` `5b55ea153303d78ebc652da2756b0995dbafc52b`. Only `ad_intelligence/analytics/analyzer.py` and `tests/test_ad_strategy_analytics.py` are selected from the isolated Luna patch. The shared checkout's unrelated dirty paths remain untouched and unstaged.
- Sol independently copied those two files into a clean archive of exact HEAD, explicitly set that directory as cwd/PYTHONPATH, and used a fingerprint-matched disposable `LUMENIS_TEST_SEED_DB`. `python -X utf8 -m pytest -q tests/test_ad_strategy_analytics.py tests/test_batch2_intel_security.py tests/test_bmp_truth_isolation.py`: exit 0, 101 selected tests passed, no background-thread leak. `compileall` and the AI-native constitution gate passed. Production `data/monitor.db` SHA-256 before and after: `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; no sidecars were present.
- A first Sol archive command had invalid PowerShell argument syntax and exited 1 before any test. Luna's earlier tests ran from the shared checkout and are marked `INVALID / NOT ADOPTED`; its corrected isolated run passed. Only the final explicit clean-snapshot test above counts toward this acceptance.
- An empty ROAS input returns `None/unavailable`; a missing revenue input returns `None/partial`; measured zero revenue and positive spend still produce numeric ROAS `0.0`. A funnel missing stages preserves `None`, while observed zero remains zero. Partial data suppresses optimization advice. Partial aggregate amounts are observed subtotals, not complete campaign totals.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: judge whether an ad campaign's measured return or stage loss warrants action. `ENTRY`: existing BMP analytics analyzer. `REAL INPUT`: isolated measured and missing metric cases, not live campaign data. `END-TO-END PATH`: input normalization → explicit completeness state → calculated or unavailable/partial result → advice guard. `USER-VISIBLE RESULT`: none in this Batch; no product ViewModel or actual campaign feed calls this path. `FAILURE/RECOVERY`: supply the missing observed metrics and rerun; no invented zero or premature advice is returned. `EVIDENCE`: clean-snapshot 101-test regression, compilation and constitution gate above. `ACCEPTANCE ASSERTION`: the bounded truth repair passes; ROUND 12/13 still need real user-work E2E and remain `REWORK`.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no new ad accounts, brands or campaigns. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Canonical random-entity sample count is zero because no production population is read here.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. Genuine data access, rights, Permission, creative/context linkage, an operable BMP job and outcome evaluation remain unverified.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [Google Ads' official conversion-value-per-cost definition](https://support.google.com/google-ads/answer/13405059?hl=en) (accessed 2026-09-26) divides observed conversion value by observed cost. Decision `ADAPT` only the principle that a denominator and numerator must be measured before a return ratio is claimed; it does not make Google Ads a LUMENIS data source or create a new integration. `DEFER` campaign optimization and cross-platform comparisons until platform-specific lineage, permissions and real outcomes exist. No new library, model or score was added. Scoped regression and mainline revert are the rollback route.

`NEXT DEPENDENCY`: bind authorized, source-backed campaign metrics to a real BMP task and show honest unknown/zero states through the existing ViewModel, then validate the user action and later outcome.
