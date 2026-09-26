# ROUND 06 — Public HTTP native identity binding

Status: bounded SYSTEM Collector source/test Batch TESTED. ROUND 06 remains REWORK / LIVE_NOT_VERIFIED.

## Exact change

At base `66d157317dde24f5e8702db070dce854b1f2a19b`, `PublicHttpAdapter` produced a stable `platform_content_id`, but `_native_record` did not map it to the `content_id` required by the existing canonical importer. The native record now carries that same ID and the item's publication time under the existing `public_http` platform branch. No new collector, storage, Evidence or Permission owner was created.

## Verification and limits

In an isolated clean worktree, `python -m pytest --noconftest tests/test_public_source_adapters.py tests/test_secondary_collection_surface.py -q` returned **28 passed, exit 0**. The regression exercises the real importer with a stubbed `database.insert_note`; it checks stable `public-http:` identity, source URL, platform and publication time. `git diff --check` and the AI-native Constitution Gate returned exit 0. No production database, Cookie or personal account was used.

The attempted live [ONS retail bulletin](https://www.ons.gov.uk/businessindustryandtrade/retailindustry/bulletins/retailsales/august2026) fetch returned `PROVIDER_UNAVAILABLE` from the public-source SSRF guard before source bytes were received. Its failure Evidence is not a successful Canonical import. The Evidence call still lacks explicit global domain/product scope, and a real actor/session is required for the scoped read API. This Batch does **not** prove live Source → Evidence → Canonical → user result, Global coverage or Round 06 completion.

REAL DELIVERY CARD: job = inspect a real authorized public commercial signal; entry = explicit manual public collection; real input = ONS bulletin URL, attempted but not fetched; end-to-end path = public adapter → Evidence → canonical importer → scoped read; user-visible result = not verified; failure/recovery = transport/source guard returned unavailable and recorded failure Evidence; acceptance assertion = not met. COMMERCIAL OVERLAY IMPACT: none accepted. GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial NO, Global Brand NO, Guangzhou reference PARTIAL.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: The official ONS bulletin (accessed 2026-09-27, 2026-09-18 release) states Open Government Licence v3.0 subject to exceptions; [ONS terms](https://www.ons.gov.uk/help/terms-conditions) and [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) permit commercial reuse of covered text/data with attribution, while excluding some third-party media. Decision: ADAPT the existing public HTTP owner for text/data only; no media intake or new dependency. Live source acquisition and scope/Evidence binding remain separate gates.
