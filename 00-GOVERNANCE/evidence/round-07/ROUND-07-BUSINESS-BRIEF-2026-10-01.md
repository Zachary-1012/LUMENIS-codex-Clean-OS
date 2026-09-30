# ROUND 07 — question-driven CTH/BMP report draft

Base: local HEAD and fetched origin/main `06cb5d474ecc73d22a5812e2db31cb239d5daf5e`.
Existing Shared Reporting owns report artifacts; SYSTEM AI Gateway owns model
execution, Shared Evidence owns signed derivative provenance, Evaluation owns
review records. No new store, business owner or frontend authority.

## Bounded Task Card / source context

Locators: `cth_job:outcome`, `evaluation_learning:outcome`,
`reporting/source_brief_job.py:decision`. Relevant current sources are
operational_brief, source_brief_job, media_brief, AI Gateway core and the report
routes. Historical CTH-DATA-INTELLIGENCE-ADOPTION-2026-09-27 and
FULL-PRODUCT-UPGRADE-CLOSURE-RESEARCH-20260929 inform the distinction between
source statements, interpretation, proposed action and observed outcome. They
do not prove implementation. The current BMP-07 quota/cooldown source is not a
campaign outcome owner; it is not reused as ROI Evidence.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: ask a venue or brand question, inspect a grounded research
  draft with source excerpts, inferences, proposed checks and missing inputs.
- ENTRY: existing exact-scope Source Brief generate/reopen API; optional
  `business_question` (4–1500 characters). Frontend remains paused.
- REAL INPUT: writer-authenticated scoped Canonical content through the existing
  reader. Default source-only reports remain unchanged. No content is obtained
  from title-only records or other scopes.
- END-TO-END PATH: server actor/Permission → exact Canonical scope → bounded
  body excerpts → local-only Gateway structured inference → schema/citation/
  exact source-and-fragment selection → signed derivative Evidence → immutable report
  snapshot → reopen and signature verification.
- USER-VISIBLE RESULT: `business_analysis` includes a Markdown draft, structured
  observations/inferences/proposals/unknowns, exact source IDs, model and
  derivative Evidence. Source excerpt equality is not independent fact checking.
- FAILURE/RECOVERY: no body means unavailable without model execution; timeout,
  invalid output or persistence failure preserves the source report with an
  explicit analysis failure. Reopen never re-runs inference; signed Evidence
  mismatch blocks replay. Retrying failed media retains the business question
  in a new report. Existing report resume retains the immutable original.
  Rejected model candidates now retain separate signed diagnostic Evidence
  (`REPORT_BUSINESS_ANALYSIS_REJECTED`, result FAIL), never accepted analysis.
- EVIDENCE: verification/live results below. HUMAN_PENDING remains mandatory.
- ACCEPTANCE ASSERTION: bounded draft/lineage/reopen behavior only. No action
  executed, no business outcome observed, no human usefulness acceptance.

Analysis input is explicitly bounded to the latest eight nonempty verified
bodies and 1200 characters per body. The result records analyzed/omitted counts,
truncation and PARTIAL coverage. This is not full-universe research, relevance
ranking, or a claim to have consumed every source. Publication time and capture
time remain distinct; neither is manufactured.
The first version produces one observation, one interpretation, one proposal
and one or two unknowns. It is an initial research draft, not a full proposal.
Body hashes, source timestamps and sample accounting remain in signed Evidence;
only source IDs, text and publication times are needed in the model prompt.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-10-01: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
ADAPT JSON-schema constrained local completion with independent application
validation. Reuse installed Ollama/Qwen3.5 and their already registered license
and replacement boundaries; no new dependency/provider. Shared hardened
loopback/no-proxy/no-redirect transport serves existing vision and structured
text calls. No external API fallback or persistent config change.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No baseline additions or collection change. Global Commercial Coverage and
Global Brand Coverage remain NOT VERIFIED; Guangzhou depth remains PARTIAL;
FULL_UNIVERSE_READY=NO. A report over a bounded sample is not coverage.

## COMMERCIAL OVERLAY IMPACT

Real business Outcome, repeated Product Owner review, time/cost/trust comparison,
hosted same-SHA acceptance and product-owned independent deployment remain open.
Codex Cloud is the development environment, not product deployment.
RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO. No Round PASS from this Batch.

## Verification

Final current-snapshot targeted verification: 71 tests,
zero failures/errors/skips, normal conftest and
explicit disposable v18 seed. It covers report/service/routes, body grounding,
forged excerpts/references, exact actor/scope replay, signed Evidence tampering,
model failure, local structured/vision transport and existing media binding.
No background thread leaks. Current Python compile and Constitution gate pass;
final publication and runtime results are recorded below.

Live preparation used the canonical WAL-consistent backup
`data/backups/pre-business-brief-20261001.db`. Four initial attempts preserved
source reports with analysis unavailable after 120-second local model timeouts.
Their immutable jobs are `brief-fd674c2278c94efdbb17ab97e1bbd8a2`,
`brief-0acaf2a2cba640789d14d55ef6b80cea`,
`brief-e8ecd2bc924445c39899179ebfb57a30`, and
`brief-bd556d250acf4188b17eae24f270ca03`. Reopen matched and wrong-scope read was
403 in every case. These are failure/recovery evidence, never successful analysis.

The local runner reported about 23 prompt tokens/second on CPU: a 2542-token
prompt consumed 110 seconds before useful generation. Compact output alone did
not fix it. The report now omits duplicate provenance metadata from the prompt
and requests a separately bounded 180-second text timeout. The default text
and existing vision timeout remain 120 seconds; no global configuration or
user model selection was changed. This does not prove interactive latency or
independent product hosting.

After prompt/timeout correction, jobs `brief-714d7937fbe7458fba1d1f784be26272`
(168.49 s) and `brief-fb8398cc885f40bbbbe7633257cd9e17` (108.38 s) returned model
outputs but failed grounding/schema validation. They remain unavailable and
immutable. The next correction makes the model select a source ID and original
180-character fragment index; the application restores the exact excerpt and
rejects nonexistent indices. It does not relax citation or source checks.

### Real drafts and quality disposition

The same production API generated and identically reopened these signed drafts:

| Domain | Job | Derivative Evidence | Seconds | Quality disposition |
| --- | --- | --- | --- | --- |
| CTH Guangzhou | `brief-840daf4d2c864fea86096d1f29d76833` | 426 | 143.71 | UNKNOWN / human review pending |
| BMP Nike v1 | `brief-51c17cbdff4d4a51baa77d638aad1be8` | 427 | 99.60 | FAIL, engineering review |
| BMP Nike v2 | `brief-2b97d7bb73114fd38a5aa2967009688e` | 428 | 115.96 | FAIL, engineering review |

Each consumed five existing scoped sources, recorded PARTIAL/truncation, and
rejected GLOBAL access to the focused job with 403. Guangzhou proposes turning
anniversary stories into an offline activation, but its emotional-demand
inference is not consumer research. Its quality value is NULL. Nike v1 treated
a social post's simulated dialogue as an internal/financial signal and distorted
a proper name/number. v2 recognized the fictional dialogue but still speculated
about a product name and selected a tiny word suffix as its quote. Both have a
persisted quality value 0 / FAIL, explicitly engineering judgment, not a measured
campaign outcome or Product Owner decision. The API returns these evaluations
alongside the exact artifact. No failing draft is accepted for client use.

Version 3 fixes fragment context: short sources up to 500 characters stay whole;
longer excerpt windows are 400 characters, with tails under 100 merged into the
previous window. Concatenation preserves exact original bytes/text. The
versioned reader still reopens signed v1/v2 drafts. This final correction is
tested; a new v3 semantic model acceptance run remains NOT VERIFIED. Do not
conflate source/citation integrity with useful business analysis. Next work is
source relevance, semantic evaluation and product review/rejection handling,
alongside the existing scoped durable-task recovery gap.

Final protected DB: notes=270, Canonical=270, daily_reports=31,
evaluation_records=64, ai_task=0, ai_task_step=0, integrity=ok, FK violations=0.
No source facts, timestamps or Canonical scopes were rewritten. Reports and
engineering quality records were appended through their existing owners.
Current source is TESTED; scoped live draft/artifact/review behavior is verified;
business-quality acceptance remains REWORK / HUMAN_PENDING. No Round acceptance.
