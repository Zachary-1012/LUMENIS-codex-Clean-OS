# ROUND 07 / J3 + J7 — owned AI milestone and real task materials

Base: `88ed522f00c996982010b9abfc232a17cfefe710`, fetched and verified on
2026-10-01. Scope: existing SYSTEM AI Gateway, Shared Reporting/Learning,
existing Collector intake. Unknown `work/`, source data, old artifacts and
user model configuration are protected. No new owner or acceptance round.

## Current objective correction

The Product Owner explicitly stopped local-model and Zhipu use in product and
development, retaining interfaces only. The proposed 300-second Ollama retry
was cancelled before invocation; the uncommitted timeout expansion was removed.
Typed timeout error handling remains useful interface behavior, not a reason
to resume those providers. Codex Cloud is development infrastructure only.

The active objective retains the original five technical items and J1–J8;
the sixth item, repeated real-user operation, is deferred to consolidated
product acceptance by the Product Owner's latest instruction. It is not PASS
and does not prevent independent technical work. The native Goal remains
active; the available Goal API cannot edit objective text. This correction
supersedes its stale cloud-deployment wording without falsely completing or
replacing the unfinished Goal.

Owned AI must consume actual evidence, analyse and create useful results,
learn from task/report/review cases, validate a version on held-out work and
operate without the retired providers or Codex doing the user's task.
`provider_disabled`/unavailable is an interim diagnostic, not milestone closure.
No owned trained inference model is established by the work below.

## Context and research decisions

Current owners were resolved with `locate_capability_context.py` for AI Gateway
and Evaluation/Learning. Existing Reporting source selection, immutable reports,
operator review and evaluation are reused. The new learning direction is mapped
into the existing J1–J8 research plan, including OpenAI, Codex, ChatGPT, Claude
and Meta Muse. No new dependency, model download or external inference call.

Nike's existing 29 records included finance, basketball, corporate information,
satire and a single creator's commuting/running observation. These do not establish
consumer demand for a running-shoe brief. They were retained rather than rewritten.

The bounded research task opened eight sources. The following three were selected
for a Nike running-footwear task and acquired through the product's existing
PublicHttpAdapter -> exact DATA_IMPORT approval -> Raw -> signed Evidence ->
Canonical BrandFocus path. Discovery was Codex-assisted public-web research;
the product did not autonomously discover these URLs.

| Material | Real publication time | Source role / use limit | Canonical / Evidence |
|---|---|---|---|
| [Nike Pegasus 42 release](https://about.nike.com/zh-Hans/newsroom/releases/nike-pegasus-42) | 2026-02-24T07:00:00-08:00 | Brand's product-positioning and technical claims; not independent consumer evidence | `public-http:89c8863da72e3bffc5b2ae8cf285b2ac` / 440 |
| [RunRepeat Pegasus 42 test](https://runrepeat.com/nike-pegasus-42) | 2026-04-25T16:19:32+00:00 | Independent test with its own methods and affiliate context; no claim about Chinese population preferences | `public-http:ca8342c14333ad3d152621379de01f82` / 441 |
| [Nike After Dark Tour](https://about.nike.com/zh-Hans/newsroom/releases/2026-nike-after-dark-tour) | 2026-03-11T10:00:00-07:00 | Attributed brand campaign; Shanghai stop is market context, not proof of product demand or official event-shoe status | `public-http:f0c796a09459c9dd5651a8ad16d2dcda` / 442 |

Exact BrandFocus: `BRAND-8b9f5ffaeea603d31bf0d7e8`. Missing engagement remains
missing. Readability/import does not grant commercial redistribution or weight
training rights. Full review text is capped by the existing collector; do not
describe it as an untruncated article. No publisher images were copied to Git.

Other opened research inputs remain references, not product intake or Nike Truth:
Nike China product page (date UNKNOWN), Runner's World Pegasus review, Chinese
marathon shoe-preference survey, standing-comfort research and the China road-race
industry report. Generic running/standing studies cannot be assigned as Nike
consumer evidence. A new source pack can add them only with the correct market
context and task need.

## Real application and recovery

Canonical backup before product writes:
`data/backups/pre-nike-task-materials-20261001` (8.67 MB, private/untracked).
All three approved imports returned SUCCESS, each Raw import=1 and Canonical
sync=1. Actual DB integrity=ok and FK violations=0. An earlier temporary helper
resolved a temporary empty database and was rejected by scope validation; those
attempts did not import product data and are excluded from success counts.
Execution then used the explicit canonical product DB and existing safe DNS
configuration; no DNS/SSRF rule was disabled.

Actual Product Core `/api/experience/reports/source-brief/generate` consumed only
the three explicit source IDs. Report `brief-c9b2f808ae8a49c6a919171818d6cf62`
has artifact hash `a4466fabd33b04ed7241f066a352899c8b3bea02d416409c4adbf2a32fce4cd5`.
Returned sources carried signed scope refs 440/441/442; exact reopen matched.
This invocation deliberately requested a source brief only; business analysis
state=`not_requested`. It is real intake/reopen evidence, not useful-AI completion.

## Independent cloud verification

Existing Codex Cloud task `01a0f350-f55f-75d6-ac80-75b74fc37033` fast-forwarded
cleanly to the base SHA and verified the same SHA before/after. Report suites:
55 passed in 17.80s, exit 0. Constitution and takeover gates: exit 0. Three old
startup/migration tests reproduced failures (exit 1), requiring repair; this is
not an overall cloud PASS. No product DB, cookies or local dirty files uploaded.
Cloud evidence: `/workspace/.lumenis-cloud/verification-88ed522f-20261001T041430Z/`.
The user confirmed the permitted cloud account; technical account identity was
not exposed by the platform. Codex Cloud is not GitHub hosted Product/App CI.

## Real delivery card / 真实用户工作闭环验收

REAL USER JOB: prepare task-relevant Nike running-footwear evidence for a brand
brief and preserve it for product analysis/learning. ENTRY: approved acquisition
and existing Source Brief API. REAL INPUT: original public sources above.
USER-VISIBLE RESULT: saved, reopenable scoped source report. FAILURE/RECOVERY:
scope refusal preserved data; exact reopen succeeded. ACCEPTANCE ASSERTION:
real input and report persistence verified; AI usefulness/training/independent
operation not yet accepted. Product Owner performs final repeated user E2E later.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: three relevant sources are not global
coverage. COMMERCIAL OVERLAY IMPACT: RELEASED=NO, OPERATING=NO,
COMMERCIAL_READY=NO. CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:
methods and owner mapping recorded in the existing research plan; no proprietary
model capability is inferred from documentation.

## Report input repair and scoped verification

The actual Reporting job no longer always reads the first 1,200 characters of
each selected article. It selects one contiguous, verbatim 1,200-character window
using the business question's Chinese/English lexical terms. Original body hash,
selected offsets, truncation and term-match count are retained in the derivative
input. This is bounded retrieval, not semantic analysis or a trained model;
`semantic_relevance=NOT_EVALUATED` remains explicit. Source Truth is unchanged.

The current real Nike sources produced windows 189–1389, 800–2000 and 0–1200,
respectively. Each was checked against its original Canonical body, retaining
scope Evidence 440/441/442. These checks are source-owner runtime evidence;
they do not establish a new AI-generated business result.

Six affected Reporting modules passed 104 tests, zero failures/errors/skips,
exit 0 in 126.131 seconds, using the explicit disposable v18 seed. They include
real route tests for late-article Chinese/English task material, exact scope,
immutable artifact reopen, missing/foreign inputs, revisions and recovery.
Model responses are mocked only in tests; tests are not product AI acceptance.

The three clean-cloud failures were repaired without weakening the assertions:
migration tests pin the current canonical v18 and preserve NULL/history/backup
checks; the AUTO test first builds a valid Registry-owned plan, then asserts the
original default-OFF error before identity work. Both full modules passed 17
tests, exit 0. Those fixes have not yet been re-executed in GitHub hosted CI.

Fresh read-only product DB check: Canonical=273, Evidence=442,
evaluation_records=121, UNASSIGNED=4, quick_check=ok, FK violations=0.
Evaluation rows include technical checks and failed/unknown usefulness reviews;
their count does not establish observed business impact. The four remaining
unassigned XHS items retain their documented negative/insufficient scope result.

## Retirement enforcement, current gates and actual Core

Canonical Gateway/Provider/Channel and LocalAIClient entries now reject retired
local/Zhipu routes before probes, transports, cache reuse or fallback. Registry
status mutations cannot undo retirement. Active-but-offline transport remains
`unavailable`, distinct from policy `provider_disabled`. The existing app heartbeat
also requires actual output, so an unavailable provider is not reported healthy.
Nine focused modules passed 205 tests in 7.033 seconds, exit 0, zero failures,
errors or skips. These tests use mocked transports and an isolated database.

The boundary validator's old requirement for a removed root `permission_gate.py`
was corrected to the current `lumenis/system/security/permission.py` owner. The
missing-owner HIGH remains blocking; a legacy root file cannot substitute for it.
Two regressions plus both startup/migration modules passed 19 tests, exit 0.
Boundary CI now exits 0 with zero HIGH/CRITICAL findings; nine existing MEDIUM and
eleven INFO findings remain visible. This is not a claim of a clean security audit.
Constitution and takeover validators passed. Final staged-source compilation and
co-publication checks are required before commit.

The exact supervised Core child tree was reloaded; supervisor PID 19440 remained
and Core recovered on 127.0.0.1:8201 with PID 5108. `/healthz` reports healthy with
database ok. The actual status API reports `ai_enabled=false` and
`ai_provider=provider_disabled`. The earlier three-source report reopened exactly
unchanged. Before the new runtime write, the canonical owner created private
backup `data/backups/pre-provider-retirement-runtime-20261001` (8.80 MB).

An actual three-source business request returned in 0.813 seconds with explicit
`BUSINESS_BRIEF_PROVIDER_DISABLED`, no analysis and no replacement provider:
job `brief-5879d1cf0bc94881bece334f46bf9385`, artifact
`09479059f2b75f1b3593ee97ba3e8a8266edcda2136f539b31d25da9b0cd3a5f`.
Exact reopen succeeded; the existing three artifact/evaluation checks persisted.
Post-write integrity=ok and FK violations=0. This proves retirement/recovery,
not owned reasoning or useful-analysis success.

Remaining technical exit: useful owned text/visual analysis with the real input,
its grounded task outcome and evaluation, and same-SHA Product/App hosted execution.
Repeated human use remains deferred to final consolidated acceptance. No trained
owned inference implementation has been verified; neither the source-window
selector nor a source brief may be relabeled as that implementation.

The AI-OFF neighbor regression also passed (one test, exit 0); its business-rule
continuity checks remain, while retired-provider expectations and process-state
restoration now match the current policy. Total distinct scoped tests: 329.
Final staged snapshot: 27 files, 23 Python files parsed successfully; diff check,
Constitution and takeover gates exit 0. The credential-path diagnostic still
flags two pre-existing Flutter `profile` manifests by pathname. Inspection found
only Android INTERNET and macOS development entitlements, no credentials; neither
file is staged here. This diagnostic remains recorded, not relabeled as PASS.
