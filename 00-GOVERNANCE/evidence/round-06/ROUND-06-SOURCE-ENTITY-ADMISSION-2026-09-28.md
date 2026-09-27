# ROUND 06 — source/entity admission

Base: ec0bc86c7f03e1ca194bac4d4d876645b7f49e61.

## Defect and bounded fix

Root's later real query for Shenzhen MixC Luohu incorrectly assigned three
Shenzhen Bay posts (7563830274112359737, 7566484323726101775,
7679739125724925227). Search authorization only authorizes an operation; it does
not prove returned posts concern the chosen venue. Existing frozen-scope writers
require a separate audited correction; no source records or original Evidence
were deleted. The private before-correction SQLite backup passed integrity/FK.

The existing Collector now requires an unambiguous registered-name mention in
the actual title/content before this social prelaunch path promotes exact scope.
Search query, matched_keywords and author name cannot supply that mention.
Latin names require word boundaries; registry-name collisions remain reviewable.
This is association evidence, not verification of source claims. Other matching
methods and human-reviewed aliases remain future improvements in the same owner.

A mixed result persists only its admitted source IDs. Evidence records the
admission decisions and its success covers that subset only; the overall call
returns PARTIAL_SCOPE_REVIEW_REQUIRED, ok=false and refresh_verified=false.
An entirely unresolved batch writes no Raw/Canonical/native business rows.

## Verification

Current isolated source (production DB not used by tests):
- 18 tests: source mentions, Douyin exact approval/denial, mixed-result integrity,
  idempotence, native-field preservation and Atom regression; exit 0.
- 2 public exact-scope import regressions; exit 0.
- Three final source/test files AST parse PASS and staged bytes match candidate.
- A real narrower Shenzhen query on a disposable product clone returned two
  unresolved records and one explicit name mention. Initial all-or-nothing guard
  refused import, which exposed the need for the subsequently tested partial path.
  That early live check is not claimed as live proof of the final partial writer.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: collect relevant social content without confusing similarly named venues.
Entry/input: explicit manual Douyin query and canonical CTH/BMP registry scope.
Path: source content -> identity admission -> admitted IDs -> Raw -> signed
Evidence -> Canonical/native fields. Result: honest accepted/pending counts.
Recovery: unresolved identities require review; signed historical mistakes need
append-only correction evidence and an explicit current-scope transition.
Assertion: irrelevant content cannot silently become an exact scoped fact.
Real user interface/workflow E2E: NOT VERIFIED. Existing erroneous product rows:
CORRECTION PENDING, not repaired by this source patch.

## Scope/status

No new owner, schema, product account or platform automation permission.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: existing registry and
source-matching owners inspected; legacy Guangzhou-specific heuristic not reused
for other entities. This is a runtime-defect repair, no new dependency adopted.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: contamination is a blocker, counts do not
prove coverage. COMMERCIAL OVERLAY IMPACT: no readiness promotion.
ROUND 06 REWORK; full-universe, RELEASED, OPERATING, COMMERCIAL_READY NO.
