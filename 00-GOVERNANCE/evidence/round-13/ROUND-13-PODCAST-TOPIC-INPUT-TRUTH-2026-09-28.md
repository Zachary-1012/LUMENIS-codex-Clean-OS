# Podcast topic input truth candidate

Status: LOCAL CANDIDATE / TESTED / ISOLATED_HTTP_VERIFIED, not integrated,
published, USER_VERIFIED or completed podcast workbench. Root approved this
independent bounded batch after the exact-resource import bundle was frozen.

## Baseline and scope

Fresh canonical main HEAD and origin/main at batch start:
`ac27acf543b9c9f86eb9ede5e2d9b429f58782cb`.
The canonical worktree's protected podcast_routes.py difference (+15/-60) disables
unscoped entity access and startup DB initialization. Its exact dirty bytes were
archived and preserved as the patch baseline; those changes were not rolled back.

Baseline SHA256:

- podcast_routes.py: `6BAEBBF276305842F7661FEAE584811D1DC87073156FE0643B385DEBD4E780C5`
- podcast/intelligence/topic_scoring.py: `E5AA8A379DC02E970BBB6DE535E18BBF413CA2DC4B630F77D305A0B576CC79DC`
- tests/test_podcast.py: `93F7ED2AE19165269FC8C3E1121E2F068BA66D3331F71FED9181A517DD23218A`

Only the actual topic-score route/algorithm and two scoped tests were changed.
Sibling topic_score.py, scope/v19, BMP08/UI, media/video bundles and production
DBs were untouched. All six exact-resource frozen source/test hashes still match.

## Behavior

Missing/null signal values now remain None. Complete observed signals retain
the original weights, cap/floor, and classification thresholds (positive maximum
90, not a renamed 100). Explicit zero is an observed value, not missing.

| Input | Response |
| --- | --- |
| Empty or partial object, including per-field null | HTTP 200 / input_required / score=null / stage=null / named missing_signals |
| Complete numeric inputs in [0,1] | HTTP 200 / scored / existing numeric score and stage |
| Bool, nonfinite, numeric string, collection, out-of-range value or invalid body | HTTP 400 / invalid_input / score=null / stage=null |
| Unexpected scoring dependency failure | HTTP 503 / unavailable / no private exception detail |

The API no longer silently coerces strings, clamps out-of-range values or treats
invalid JSON as an empty request. Two old test inputs whose intent was an explicit
zero baseline now specify all zero fields; assertions were preserved/strengthened,
not skipped. Source formula and sibling owner were not replaced.

## Current snapshot verification

Before repair: four targeted tests failed, demonstrating empty input became 0.0.
After final edits: `test_podcast_topic_signal_truth.py` + `test_podcast.py`:
**169 passed in 3.82s, exit 0, no skips, no background thread leaks**.
Explicit new empty test seed and test-local storage, never a production DB.

An independent non-pytest HTTP run bound a temporary 127.0.0.1 ephemeral port and
exercised the actual blueprint using stdlib HTTP. Eight requests covered empty,
partial explicit zero, null, complete zero, complete old weights, bool, NaN and
invalid body. All expected status/state/score/stage assertions passed, exit 0;
sqlite connect was guarded and database_open_attempts=0. The temporary server
and thread were closed. This is isolated API evidence, not user E2E or a live
production application. Flask 3.1.3 / Werkzeug 3.1.8; current upstream make_server
documentation was consulted through Context7. No new dependency was installed.

Final SHA256:

- podcast_routes.py: `0DB1EE1756486AA343DB03FE62D7F5676FF3023636E556ED33F4776EF9ADD9D4`
- podcast/intelligence/topic_scoring.py: `244F32BDD0035B0E5BE2744A74BC1846421C1C2A8894A84E49AB348186395E95`
- tests/test_podcast.py: `D62B203E397554FC956AEB759495957BDE44695198F216D0CD68872B876ADDD0`
- tests/test_podcast_topic_signal_truth.py: `4C14E2E32C15908EB646422944C0A2022921016C7C6189997F6DB84931781A6A`

## Real delivery and continuation

REAL DELIVERY CARD: real user job is evaluating a podcast idea without mistaking
unobserved evidence for poor quality. API entry now distinguishes required input,
invalid input and scored results. The approved workbench still needs to bind these
states, gather provenance-backed or user-entered signals, expose rationale and
preserve editable review/history. No current model, platform-data quality, episode
production or publication acceptance is implied by deterministic scoring.

COMMERCIAL OVERLAY IMPACT: COMMERCIAL_READY=NO. GLOBAL UNIVERSE / DATA MATURITY:
no coverage change; unknown inputs are not converted into measured zeros.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: bounded input truth repair
under existing Content & Creation/Podcast owners; companion quality research
separates measured audio, factual support, human preference and outcome feedback.
No new owner, AI provider, Permission/effect, store or automatic learning promotion.

Root must apply the exact patch against its protected baseline, rerun integrated
regression, bind actual workbench states and publish through normal gates.


## Root integration at accepted main

The first integration against clean accepted main produced 168 PASS / 1 FAIL:
the candidate relied on an existing local-only podcast entity scope fence. The
failing regression was retained. Root inspected that exact protected route delta
and legacy podcast_entities schema: entity routes lacked canonical actor/domain/
focus columns and blueprint registration initialized the legacy store.

The unique existing fence is now included: four entity read/write routes return
PODCAST_ENTITY_SCOPE_UNAVAILABLE before storage access; registration no longer
creates tables. This preserves the schema/Permission blocker until the existing
scoped migration/API work is accepted. It does not replace that work, delete
entities or claim podcast workflow closure. No product DB migration/write ran.

Root added checks for all four denied routes and forbidden startup initialization.
The integrated current snapshot passes 173 targeted tests, exit 0, no skips or
thread leaks; all four changed Python files parse. Root separately reran eight
real loopback HTTP requests against this snapshot, exit 0, DB-open attempts 0,
server stopped. Missing input remains null/input_required, explicit observed zero
is preserved and invalid data is rejected. No test or gate was weakened.

The existing stateless scoring route is corrected; actual workbench binding,
scoped entity persistence, user review and real user E2E remain open.
ROUND 13 remains unaccepted; USER_VERIFIED/RELEASED/OPERATING/COMMERCIAL_READY NO.
