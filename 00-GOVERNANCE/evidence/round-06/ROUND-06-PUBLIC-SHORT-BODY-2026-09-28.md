# ROUND 06 — short public content and source identity

Base: `0d52670e3944e75fd3c70d9fd21d9551f411dbd5`. Owner: existing SYSTEM
Collector `PublicHttpAdapter`. This is a bounded parser correction, not a new
source registry or data authority.

## Real source finding

At 2026-09-27 19:30 UTC the existing safe public HTTP transport fetched:

- `https://thehyundaiseoul.ehyundai.com/about/location`: 67,881 bytes; the existing
  parser already retained 1,160 Korean characters and the real address. The
  candidate's English anchors were wrong for this Korean page. Its site-wide
  homepage canonical was also collapsing the location page's identity.
- `https://www.ikea.com/kr/ko/stores/`: 832,562 bytes; real semantic article 196
  characters was discarded by the 500-character floor, leaving a generic
  95-character description. The page lists native store names; it does not
  establish the detailed Gwangmyeong street address.

Both captures used no Cookie or account. Raw HTML remains outside Git in the
local verification directory. No commercial redistribution permission is inferred.

## Change and verification

Semantic article/main/accessible-main content is retained even when short;
heuristic CSS containers keep their existing noise threshold. A detail page's
homepage canonical is rejected while a same-page canonical may still remove
tracking queries. No existing DB content or identity is rewritten.

On the isolated accepted-source archive plus this exact candidate:

- `tests/test_public_http_body_quality.py` and `tests/test_public_source_adapters.py`:
  16 passed, exit 0, no thread leak.
- `tests/test_public_http_article_extraction.py` and `tests/test_public_source_transport.py`:
  26 passed, exit 0, no thread leak. DNS/pin/redirect safety remains enforced.
- Constitution Gate: PASS, exit 0.
- Reprocessing the two actual captured responses retained the Korean address
  and store names, preserved both exact page URLs, and kept publication date
  UNKNOWN. This is captured-response verification, not a second live fetch.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: collect a short public location/directory page without losing its facts.
Entry: existing public collection path. Real input: the two source pages above.
Result: corrected normalized source content and stable page identity.
Failure/recovery: existing transport failures and unavailable publication time
remain explicit. No product DB apply, user page, downstream report, or real-user
E2E was performed in this Batch. ROUND 06 remains REWORK.

COMMERCIAL OVERLAY IMPACT: no rights promotion or commercial completion.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: both Global coverage states NO / NOT
VERIFIED; Guangzhou reference PARTIAL. Full Universe, RELEASED, OPERATING and
COMMERCIAL_READY remain NO.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT based on the two
direct source captures; improve the existing parser without a new dependency.
