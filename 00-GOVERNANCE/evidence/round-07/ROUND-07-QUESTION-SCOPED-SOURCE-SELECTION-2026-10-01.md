# ROUND 07 — task-relevant source selection

**Final decision: Reporting candidate REWORK / NOT ADOPTED. Only the bounded
SYSTEM local-embedding interface is retained as TESTED, with live calls observed
during the experiments. This is not a report-quality or Round acceptance.**
The Reporting source and its tests were returned exactly to base `7d8acbf3`;
the rejected diff is preserved beside this report as
`ROUND-07-REPORT-SELECTION-REJECTED-2026-10-01.patch.gz` (uncompressed SHA-256
`0848d120cd677ea414f126f6b4e0158bc6ddf25e87e0aea9b1baa2678c8666dd`).
It is research evidence, not executable production source or an instruction to
apply it. Existing untracked `work/` was untouched.

## Bounded context manifest / Task Card

- capability: Reporting / AI Gateway, query: source relevance.
- remote_head / local_head: `7d8acbf37647cddb84ec11131951e3811bab7a32`.
- dirty_paths_preserved: true; pre-existing untracked `work/` is protected.
- owners: existing Shared Reporting and SYSTEM AI Gateway; no new truth store.
- rules: AGENTS execution router; AI-native Constitution principles; current
  Product Architecture and Source Owner Index; Real Delivery Overlay acceptance.
- implementation: `reporting/operational_brief.py`, `source_brief_job.py`,
  `ai_gateway/core.py`; existing Canonical exact-scope listing remains authoritative.
- prior evidence: business-v4 actual Nike FAIL, Guangzhou UNKNOWN; latest-capture
  selection excluded relevant older sources already in the same Canonical scope.
- historical input: existing semantic memory / brand knowledge caller inventory
  is reference-only; neither may become a second Canonical retrieval owner.
- task: select a bounded set from verified scoped candidates by the actual user
  question, retain provenance and honest selection/coverage state, then execute
  the unchanged business-analysis model on the real selected input.
- unresolved boundary: semantic usefulness, bounded local latency, user acceptance.

## Implementation / research decision

ADAPT existing installed BGE-M3 through SYSTEM Gateway for ephemeral embeddings;
use similarity only to order already verified Canonical sources, followed by a
bounded local task-relevance rerank. No vector DB,
cross-scope lookup, source rewrite, cloud fallback or model download. Report
selection examines at most 100 existing verified candidates and feeds at most
eight bodies. The final candidate reranker sees at most 30 verified candidates
with 100-character titles and 120-character excerpts, and can choose fewer or none; invalid,
duplicate, foreign or empty selections cannot start business analysis.
Truncation and PARTIAL coverage remain explicit. Source-only
briefs preserve their existing behavior. A ranking failure retains a source
brief but makes business analysis unavailable rather than claiming relevance.

Authoritative sources accessed 2026-10-01:
https://docs.ollama.com/api/embed (batched input, truncate=false, model identity,
vectors and observed token/duration metadata);
https://huggingface.co/BAAI/bge-m3 (MIT, multilingual dense representations;
no special query instruction required). The model card recommends stronger
hybrid/reranking pipelines for larger systems; this batch only tests reuse of
the already installed dense model against the specific observed report defect.
Third-party register records the local digest and redistribution boundary.

## Owner reuse and execution resources

The bounded source inventory found that SemanticMemory.search_assets ranks
admitted intelligence assets, while BrandKnowledgeBase.search ranks its own
knowledge rows. Neither accepts an authorized Canonical candidate list or exact
report scope. They were not copied into a new store or treated as scope authority.
OpenCode/Zhipu glm-4.7 was attempted for this two-file mechanical inventory but
failed authentication before analysis; local read-only fallback established the
facts. No provider credentials were inspected or changed. A GPT-6 Luna max worker
implemented only the Gateway function and focused tests; root reviewed the diff
and owns the Reporting integration and actual-task acceptance.

## Verification

Current scoped AST/compile, diff and Constitution checks passed. The initial
Reporting regression run found an incorrect column name in the new tamper fixture;
that test was corrected to inputs_json and all 12 source projection tests then
passed. The other unchanged Reporting tests passed in the original group. The
changed business-analysis and structured/vision Gateway neighbor group passed
35 tests. Luna Gateway embeddings regression passed 25 tests including finite
norm, exact model, no remote/cloud fallback and missing usage semantics.
Final source-projection/business-analysis regression passed 36 tests after the
task reranker was added, including scope/signature exclusion, invalid selected
indices, empty-body preservation, unavailable ranking and exact reopen.

### Actual dense-only control — rejected

Nike task `rbrief_2d00344a-d700-4928-92bd-8f5c78e10185`, job
`brief-e826f6dc8b244361818cc04a747da1e2`, signed analysis Evidence 432.
Admission 0.146 seconds; execution/reopen checks 156.72 seconds. The candidate
pool was 29 verified Canonical rows. It selected a vague save-Nike post,
navigation and corporate material; the output still failed the content-research
question. Engineering Evaluation `business-review-brief-e826f6dc8b244361818cc04a747da1e2`
is FAIL. The result and its negative feedback are preserved, not overwritten by
the later reranker. This real failure is why similarity alone is not promoted.
Actual Ollama process metadata showed CPU execution (`size_vram=0`); the
embedding and generation models were installed already, with no download or
external API used. This is one observed latency case, not a benchmark or SLA.

### Local reranker controls

The first full task with the 4B reranker (longer previews) completed as an honest
business-analysis UNAVAILABLE after 312.62 seconds; job
`brief-f80a1c8a896e45ccb6464b9d394cc406`. Its selected sources remained dominated
by financial and vague social material. Exact reopen and wrong-scope 403 held;
no analysis Evidence was fabricated. That candidate is not quality-accepted.

A read-only comparison then used already installed `qwen3.5:9b` and shorter
previews. An initial incorrectly bootstrapped standalone run had zero verified
candidates and is excluded from comparison; the helper was fixed to use the
existing environment loader and assert nonempty verified inputs. With 27 real
Nike bodies it completed in 147.58 seconds, actual model `qwen3.5:9b`, 1,628
input / 21 output tokens. Its four selections included Air Force 1 styling and
running-shoe commuting comparison, as well as Interbrand and a sales-opinion
post. This improves task material, not verification of those source claims.
Both preview size and model changed, so this does not isolate model size as the
cause. The official Qwen model card/LICENSE (accessed 2026-10-01) and installed
digest are recorded in the Third-party register; no Codex/user model default,
Windows routing configuration, new download or external API was changed.

### Final two-domain actual tasks — promotion rejected

- Nike: task `rbrief_9d5e4bfa-4f27-4547-83c8-771bfd0b63d9`, job
  `brief-64c254c4587b413c89aed2a3d5abc37d`, Evidence 433; admission 0.181 seconds,
  execution/reopen checks 350.89 seconds. Four selected sources again favored
  financial/satire material after semantic ordering. The output correctly called
  the CEO/CFO dialogue fictional, but only suggested generic comment research,
  not a usable content direction with a bounded test. Engineering quality
  `business-review-brief-64c254c4587b413c89aed2a3d5abc37d` is FAIL. The earlier
  short comparison was not robust evidence for promotion.
- Guangzhou: task `rbrief_8648c008-5448-456c-a0c3-f3653d452f78`, job
  `brief-0fda4369e90d414d9d14a51d3803a5a9`; admission 0.114 seconds, 60.87 seconds
  to honest `BUSINESS_BRIEF_RELEVANCE_UNAVAILABLE`; no analysis Evidence. A
  source-only artifact persisted and reopened. This is failure handling, not
  successful operating analysis.
- Both retained exact artifact replay and rejected a GLOBAL request for the
  focused task with 403. These runtime properties do not compensate for failed
  usefulness/latency. No more prompt-only/model-size trials were promoted.

### Retained interface / final verification

Gateway `local_embeddings` is bounded to loopback, approved input shapes, actual
model identity, finite nonzero vector norms and explicit failure states. It
does not download a model, change routing settings or fall back to a cloud API.
The final retained source snapshot passed 42 Gateway embedding/structured/vision
tests, Python compile and the blocking Constitution check, exit 0. Reporting
source/test diff against accepted base is empty. Earlier candidate tests above
describe the rejected experiment, not current main acceptance.
After reloading the stable Reporting source, all four experimental artifacts
and the earlier Nike v4 artifact reopened with identical source/analysis/artifact
bytes. Final DB counts: Raw 270, Canonical 270, reports 40, evaluations 93, report
tasks 8; integrity `ok`, foreign-key violations 0. Added evaluations and reports
are real engineering tests/reviews, not customers or successful market outcomes.

## REAL DELIVERY CARD / 真实用户工作闭环验收

- REAL USER JOB: Nike content-research direction; Guangzhou bounded activity
  research, using existing real Canonical material and the unchanged user questions.
- ENTRY: actual Core scoped Source Brief async start/status/reopen APIs.
- REAL INPUT: actual focused Canonical rows, writer-authenticated scope Evidence;
  no fixture, new collection, copied competitor output or cross-scope data.
- END-TO-END PATH: permission -> verified sources -> experimental local ranking
  -> local analysis or explicit unavailable -> existing report artifact/Evaluation.
- USER-VISIBLE RESULT: persisted drafts/failure state; business quality FAIL or
  unavailable. Frontend binding and Product Owner review remain pending.
- FAILURE/RECOVERY: failed ranking preserved the source brief; exact replay and
  wrong-scope refusal held. Failed generated drafts and their Evaluation remain.
- EVIDENCE: job/task/Evidence IDs and preserved patch above; no secrets/DB/media
  committed. The pre-write backup is `data/backups/pre-question-ranking-20261001-0920.db`.
- ACCEPTANCE ASSERTION: report-selection REWORK, not a business/real-user PASS.
  The Product Owner will perform final repeated real-user acceptance personally.
- COMMERCIAL OVERLAY IMPACT: no comparative time/cost/trust or market proof; no
  RELEASED/OPERATING/COMMERCIAL_READY upgrade.
- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; coverage remains unverified and
  source rows are preserved. No sample is promoted to global coverage.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: the installed embedding
  boundary is retained; report promotion is rejected based on actual outcomes.
  Codex Cloud is development infrastructure, not LUMENIS hosting/inference.
