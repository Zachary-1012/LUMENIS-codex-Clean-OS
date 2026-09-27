# Bilibili public native acquisition candidate — 2026-09-28

Status: research observations with a bounded field-truth correction; live Bilibili ingestion remains NOT VERIFIED.

## Current SYSTEM route

At inspected checkout `21f9637fe95cdd91a7666c61a1b64bc216be163f`, the canonical owner is `lumenis/system/collector/adapters/bilibili.py` (SYSTEM Collector). It delegates `search` to `lumenis/adapters/bilibili.py`; the v4 path checks the registered CookieVault state before calling the existing first-party endpoint `https://api.bilibili.com/x/web-interface/search/type`. SYSTEM then maps the `CollectedNote` into a `CollectionResult`. Safe local health metadata was `NOT_CONFIGURED` / `not_configured`; no secret value was read. Existing tests in `tests/test_bilibili_adapter.py` are mock-only.

## One anonymous read-only observation

On 2026-09-28, one GET was made to the adapter's existing first-party search endpoint with `search_type=video`, keyword `广州太古汇`, page 1, page size 3; no Cookie, browser, profile, or retry was used. It returned HTTP 412 with `text/html` challenge content. The request was stopped there. This proves only that this request/environment was challenged; it does not prove anonymous single-video access is always unavailable or that all authorized requests fail.

## Field semantics

Current v4 code maps `video_review` directly to canonical `comments`. The existing first-party response shape in code also preserves the original key `video_review`; the repo does not establish its meaning with primary-source evidence. Do not treat a populated field as semantically correct. Adopted bounded change: leave search `comments` as `None` until its source semantics are verified; retain `video_review` and `review` under their original raw keys without relabeling them as danmaku or comments. No verified reply/comment field was observed in the one challenged response. No claim is made about danmaku semantics.

## Sources checked (accessed 2026-09-28)

- Bilibili Open Platform docs: https://open.bilibili.com/doc — first-party docs describe app registration/identity verification, account authorization, and user-authorized data capabilities. No evidence found here that the current web search endpoint is a supported anonymous API. The page does not state a documentation license; access/commercial terms need their own review before any integration.
- Bilibili Open Platform API docs: https://open.bilibili.com/doc/4/8673959e-f7bb-56e6-6e68-d225f971b81b — docs describe application credentials/signature and OAuth access-token requirements for the documented API route. First-party; page does not state a documentation license.
- `SocialSisterYi/bilibili-API-collect`: https://github.com/SocialSisterYi/bilibili-API-collect — GitHub labels it archived on 2026-01-30; owner says the project permanently stopped and deleted docs/source after a legal warning alleging systematic publication of non-public API/access-control details. Current repository view has no usable implementation source; license is not verifiable from the archived view. Decision: DEFER/REJECT as implementation dependency or endpoint authority; do not use mirrors/forks as a workaround.
- Existing repo historical note `docs/research/2026-platform-crawling-rules.md` is dated 2026-09-07 and secondary; it is context only, not current endpoint or anonymous-access evidence.

## ADAPT / DEFER

ADAPT only within existing SYSTEM Collector and Evidence/canonical chain if Bilibili provides an authorized, supportable source path. Preserve native `bvid` as source identity; keep publish time distinct from capture time; map only verified fields. Use a verified comment/reply source for canonical comments; preserve unknown/missing separately from zero. The observed spelling of a source key alone is not proof of its meaning.

DEFER anonymous native search/detail/comments: the one search probe received 412, current SYSTEM session state is NOT_CONFIGURED, and the official documented route reviewed requires application/authentication. Do not replace this with generic HTML or claim a Bilibili native ID/author/metrics/comments from PublicHttp. PublicHttp remains its own generic explicit-URL source.

## Proposed repository path

`intelligence_library/07_Data-Evidence-Evaluation/BILIBILI-PUBLIC-NATIVE-CAPABILITY-CANDIDATE-20260928.md`

Root validation: 31 focused Bilibili/SYSTEM regressions passed on an isolated v18 seed, exit 0 and no thread leaks. No product DB write, Cookie read, challenge retry or endpoint bypass was made by this fix.
