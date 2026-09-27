# ROUND 06 — Instagram missing metric preservation

Base: `863827079446c033e74eb38cd4b3916c841c2c42`.
Owner: existing SYSTEM Instagram adapter. Provider/model: GPT-6 Luna bounded
two-file implementation; root reviewed the exact diff. No new dependency.

The adapter now applies existing `optional_int` to likes/comments/collects/shares.
Explicit zero stays zero; missing, empty or invalid inputs become None. Native
shortcodes remain strings. This does not enable Instagram or establish access.

Verification: isolated disposable DB; `tests/test_instagram_main_adapter.py`,
21 passed, exit 0, no leaked threads. Constitution Gate PASS before delivery.
No product DB write, Cookie access, external effect, or live Instagram request.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: compare actual platform engagement without inventing zero-valued metrics.
Entry: existing Instagram adapter. Input: bounded regression values only.
Result: truthful normalized values; live source, full ingestion, visible result,
recovery and real-user E2E remain LIVE_NOT_VERIFIED. ROUND 06 remains REWORK.

The accompanying capability source preserves all 34 sections and 910 nonempty
paragraphs from the supplied Word document. Its adoption map routes old claims
and deferred work to existing owners; it does not promote historical claims.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: the linked library record
pins official/GitHub findings and ADAPT/DEFER/REJECT decisions; none authorizes
new platform access or claims anonymous/authenticated field parity.
COMMERCIAL OVERLAY IMPACT: no rights or release promotion.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: Commercial/Brand coverage NO / NOT VERIFIED,
Guangzhou reference PARTIAL, Full Universe/RELEASED/OPERATING/COMMERCIAL_READY NO.
