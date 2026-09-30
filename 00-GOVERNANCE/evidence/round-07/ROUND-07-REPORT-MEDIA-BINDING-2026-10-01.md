# ROUND 07 / J4 — real image input, scoped report and Evaluation

Parent source: `ddb7e8dde7db2d4e65609d1dea51dcdb84640877`.
Owners: existing Shared Artifact/Reporting/Evaluation, SYSTEM AI Gateway and
Permission. This extends one report job, not a new media or AI system.

## Implemented boundary

- Static JPG/PNG/WebP imports retain true dimensions and `duration_sec=NULL`.
  Their earlier video-duration failure is fixed in the existing Artifact owner.
- `POST /api/experience/reports/source-brief/generate` accepts an optional
  `image_source_ref` issued by Content Source; arbitrary paths/URLs, actor IDs
  and client-authored analysis results remain rejected.
- Approved bytes, actor and exact scope are rechecked by the existing artifact
  resolver. Large images have a bounded 1024px analysis derivative; original
  bytes/hash are retained separately from derivative hash/version.
- The existing Gateway checks local vision capability and uses loopback-only
  Ollama, no proxy or redirect. Structured output is validated again after
  generation. Empty, incomplete and failed output never becomes a completed
  media result. AI output is signed **derived** Evidence, not Canonical facts.
- Signed analysis is bound to source Artifact/import execution, job, actor,
  scope, original/analysis byte hashes, provider/model and response hash.
  Reopening a report re-verifies it. Human acceptance remains `HUMAN_PENDING`.
- `resume_job_id` reopens the same persisted report/evaluations without a new
  inference. `retry_media_job_id` permits a failed-media job to produce a linked
  new attempt using its stored source ref and revalidated scope. Old observations
  are not overwritten; completed jobs cannot be retried as failures.

TaskEngine also now calls canonical `core.chat` rather than nonexistent channel
APIs, preserving completed/rule/budget/empty/error/timeout outcomes. Its existing
15-second outer thread timeout still cannot cancel an already started provider
request; this batch does not claim durable task cancellation is closed.
The adjacent Gateway blocks accidental cloud fallback for unavailable explicit
local routes and auto routing without cloud opt-in. Workstation model/config
defaults were not changed.

## Real input and execution

Official source: [Nike race-day announcement](https://about.nike.com/en/newsroom/releases/nike-debuts-a-race-day-system-of-speed-designed-for-every-runner).
The original image came from that page's asset download, not a generated fixture.
Its analysis-only use does not establish redistribution rights.

- Original: 3200x2133 JPG, 1,694,229 bytes.
- SHA-256: `77bc5896768a5f88e759b7656518a8b43be8153b776c967d9df17ca8e308277d`.
- Exact Nike BrandFocus; Artifact `ART-2666b94cdc7946bd`;
  import execution `8b748593bfa14aef`.
- Canonical backup: `data/backups/pre-report-multimodal-20261001` (private).
- Local Ollama 0.34.2, installed `qwen3.5:4b`, CPU inference.
- First completed image report: `brief-d6bd395f227b45bd8c19a6346b111c97`,
  signed derived Evidence 424; 80.44 seconds actual Product HTTP time.
  It is linked to prior failed attempt `brief-e564f8de00394724be818f309b8318bc`.
- That report and signed media reopened after a subsequent Core restart.
  Its three structural Evaluation metrics passed. These assess artifact/lineage/
  analysis binding, not correctness, business performance or user approval.

The first analysis identified three shoes, differing colour/sole designs and
visible Nike marks, but omitted readable labels and useful business implications.
It is insufficient for business acceptance. A versioned prompt plus structured
output was then added; final quality/recovery observations are recorded below.

Final structured attempt `brief-3751e8b9db2c4bb2903f25f3750fdbfa` completed
through Product HTTP in 102.45 seconds, with signed derived Evidence 425. It
correctly transcribed Nike Apex, Alphafly 4 and Swooshfly and separated an unknown
sales/availability fact. However, its recommendation incorrectly interpreted a
first starting line as a starting-performance advantage. This inference is not
established by the image. The actual Evaluation owner records the engineering
finding as `multimodal_business_usefulness=UNKNOWN`, id
`media-business-review-brief-3751e8b9db2c4bb2903f25f3750fdbfa`; it is not human
approval. There is no claim that model accuracy or business quality passed.

GET reopen and same-ID resume returned the identical signed result; cross-domain
reopen returned 403. The preceding failed attempt remains intact and linked.
At this checkpoint `evaluation_records=34` (18 before media work), Raw=270 and
Canonical=270; integrity=ok, FK violations=0. Counts include honestly failed/
unavailable media observations, not only successful samples. CPU latency and the
pending frontend binding still require user-visible workflow acceptance.

## Diagnosed failures and proportional verification

The real image initially failed a video-duration prerequisite. The old 4096-token
model context also rejected a 6327-token image/brief request. Image preprocessing,
8192-token request context and compact scoped brief context fixed that boundary.
A CPU attempt exceeded the initial 90-second timeout and remained UNKNOWN;
the bounded local timeout is now 120 seconds. No cloud provider was substituted.
Schema-invalid output remains unavailable rather than being accepted as text.

A 151-test run returned exit 0 but exposed four unintended background model
threads in legacy TaskEngine tests. It was not accepted as hermetic evidence.
The two affected unit fixtures now explicitly mock the canonical Gateway; their
unchanged 74 assertions passed with no thread leaks. The combined 160-test group
then passed with zero failures/errors/skips and no thread leaks. After the final
media/context/schema changes, 43 affected image/report/Gateway tests passed with
normal conftest, explicit disposable v18 seed and the existing FFmpeg/FFprobe.
Real image decoding, exact scope denial, signed-output tampering, failed-attempt
retry, immutable prior reports and no repeated inference on resume are covered.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: attach an approved business image to the exact scoped source brief, inspect
the derivative, save/reopen the result and retain failed-attempt history.
Entry: actual Product Core routes; the independent frontend task is paused by
its Product Owner and is not silently resumed by this backend work.
Input: existing real Nike Canonical sources plus the official image.
Result: durable report and signed analysis/Evaluation, or explicit unavailable.
Recovery: stored-report reopen, linked retry, scope denial and Core restart.
Acceptance: API/runtime binding only. Human repeated work, visual/business
quality and full CTH/BMP Outcome remain pending. Source-backed results are not
proof of faster/cheaper work than competitors or a manual workflow.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: Commercial Coverage=NO; Brand
Coverage=NO; Guangzhou reference=PARTIAL. This batch does not expand coverage.
COMMERCIAL OVERLAY IMPACT: RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO.
Hosted Product/App execution still requires the account billing/spending blocker
to clear; no repeated zero-step dispatch was performed. Codex Cloud is a coding
environment, not LUMENIS product hosting or proof of developer-PC independence.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-10-01: [Ollama vision](https://docs.ollama.com/capabilities/vision),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B). ADAPT behind the current
Gateway; preserve Evidence/Permission and replaceability. Upstream weights are
Apache-2.0 third-party work, not a LUMENIS-developed foundation model. Existing
runtime digest and license obligations are in the Third-Party Component Register.
OpenCode Zhipu/GLM-4.7 was attempted by bounded workers but failed authentication
(exit 1); none of its output was adopted and no credentials were printed.
