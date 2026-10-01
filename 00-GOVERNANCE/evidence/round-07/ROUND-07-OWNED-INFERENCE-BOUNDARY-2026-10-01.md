# ROUND07 — owned inference boundary in the existing AI Gateway

Base main/origin: db6a5b23426e8a5d2711fb0e53a641be06027b89. Preserve work/.
Task: a local Ollama HTTP address must not silently proxy a cloud model while
Reporting/Multimodal/embedding callers claim local inference. Reuse SYSTEM AI
Gateway; no provider/config/global environment/model/architecture change.

## Current facts and bounded Task Card

- Existing `_call_local_chat`, `_ollama_local_chat` and `local_embeddings` are
  the execution paths. Model metadata is resolved before text/image payloads;
  remote_model/remote_host must be absent, null or empty, then checked again on
  the returned response. Generic Ollama uses the existing no-proxy/no-redirect
  transport with an HTTP loopback URL. Non-Ollama paths keep their contracts.
- Root owns policy/research/integration. One Luna may edit core.py and directly
  matching Gateway tests. No production DB, credentials, model install, runtime
  process or external inference call in worker. Separate read-only deployment
  review cannot change files or add another runtime owner.
- Current installed Ollama is 0.34.2. Selected Qwen3.5:4b metadata reports local
  GGUF/Q4_K_M, completion/vision capability and no remote fields. This metadata
  does not prove useful business output or independence from this workstation.
- No Windows Docker/Podman executable or Ubuntu Docker/FFmpeg was found by the
  bounded commands; Ubuntu WSL2 exists. No tool/service installed or enabled.
- Product hosting target is not yet identified. Codex Cloud is a development
  environment, not LUMENIS deployment. No paid resource is authorized here.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-10-01; installed-version source pinned to Ollama v0.34.2 commit
`dfabde4539e42ba1e1eab50a3a50b88aea7958a0`:

- [API types](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/api/types.go)
  declare remote_model/remote_host on model metadata and chat responses.
- [Runtime routes](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/server/routes.go)
  show local-service requests can dispatch remotely and annotate responses.
- [Model source parsing](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/internal/modelref/modelref.go)
  supports the explicit `:local` transport selector. Chat rejects a remote model
  before forwarding when that selector is present. Preflight metadata alone has
  a check/use race if a model alias changes before execution; response checking
  alone occurs too late to protect a private prompt. Use the server-enforced
  selector together with preflight and response metadata checks, not as a model
  configuration change. Reject explicit cloud/conflicting source selections.
  Actual installed `/api/show` for `qwen3.5:4b:local` returned local GGUF and
  completion/vision capability; no remote fields. This was a metadata read,
  not inference or product acceptance.
- [Official cloud documentation](https://docs.ollama.com/cloud) and
  [local-only configuration](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features)
  distinguish downloaded execution from cloud inference. OLLAMA_NO_CLOUD=1 is
  a deployment control; this batch does not modify the user's shared daemon.
- [Docker deployment](https://docs.ollama.com/docker) is an optional execution
  packaging reference, not proof of any configured LUMENIS host or GPU.
- [Pinned license](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/LICENSE)
  is MIT. Existing dependency retained; no copied implementation/new dependency.
  ADAPT metadata/control semantics in canonical Gateway. DEFER deployment until
  a real target and its authorization are known. No foundation-model ownership
  or useful-model-quality claim follows from using these OSS components.

## Acceptance scope

REAL DELIVERY CARD: existing report/text/vision/embedding caller -> local model
metadata -> deny remote dispatch before business/private payload -> authorized
local request -> recheck response -> real output or explicit failure. Preserve
no-cloud-fallback semantics, token/time limits and model defaults. Verify denial,
local control, malformed metadata, redirects, unavailable model and propagation
through affected callers. Actual inference, hosted execution, UI and real-user
acceptance must be reported separately.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no collection, scope or Canonical writes;
Commercial/Brand coverage remains NO, Guangzhou reference PARTIAL.
COMMERCIAL OVERLAY IMPACT: no deployment, training, licensing clearance, useful
revision, business Outcome, user acceptance or product closure promotion.

## Deployment findings kept separate

The existing Docker image lacks FFmpeg/FFprobe; the staging overlay starts 8301
but inherits an 8201 health check; container loopback is not the development
host's Ollama endpoint; a fresh target needs an authorized state restore and
configuration bootstrap. No Docker executable is available on the inspected
Windows/Ubuntu runtime, so image build/start remains unverified. These source
findings do not authorize deployment, credential transfer, a new runtime owner
or relaxing the Gateway loopback boundary. A real product-host target remains
required before proving independence from the development workstation.

## Bounded runtime evidence

One benign real request through `local_structured_chat` used installed
`qwen3.5:4b`; both actual HTTP calls carried `qwen3.5:4b:local` (`/api/show`,
then `/api/chat`). The process-only cloud option was false; no .env, registry,
Codex config, daemon config, provider default or persistent model setting changed.
Output parsed exactly as `{"ok": true}`, status ollama/ok, actual response model
`qwen3.5:4b:local`, 29 prompt + 6 completion tokens, elapsed 9.64s, exit0.
Core file SHA256 during this call was
`e582fb8a853391a60f6b949800dda34c005429100952758f1c5fdc5b8b9de7a0`
and was unchanged across the request. It used no business/private input and
wrote no report, Canonical or Evaluation data. This is transport acceptance,
not model-quality, media-quality, independent-host or real-user acceptance.

The existing Gateway facade, multimodal evaluation and business-brief suites
passed 40 tests in 16.12s (exit0, no background-thread leaks), using the explicit
disposable test seed. Final changed-path regression and static results follow
below; none of these results promote J1-J8/ROUND07 or the product to PASS.

## Final scoped acceptance

- Root corrected worker model-source normalization: strip only the local
  transport marker, never cloud, when comparing embedding model identity. Final
  four changed-path suites passed 90 tests in 1.93s, exit0/no thread leaks.
- Final real `bge-m3` embedding used `bge-m3:local` for show/embed, status ok,
  one finite 1024-dimensional vector, 11 input tokens, 5.157s. Source SHA256
  `49ad86e1c1d1135b678c3a61272ec18402a58481e2dce1f1b75cee90847e1175`
  was stable across that call. The previous text call preceded only this
  embedding identity correction; no repeated report/model-quality experiment.
- Current five changed Python files compile. No existing regression, Gate,
  failure status, model default or user configuration was weakened.
- Codex Security assessment bound the immutable five-file patch SHA256
  `7d418920934d239a9caa918881625a7b13f688fb9e6be9a6538623613c989e7a`.
  Root decision is bounded source acceptance; release/user acceptance remains
  separate. Preflight plus `:local` closes the ordinary server dispatch race;
  this is not protection against a malicious local daemon. Owned deployment
  still requires suitable daemon cloud-disable/egress controls and actual
  host verification. Older servers lacking `:local` fail honestly, with no
  silent fallback to an unqualified model name.
- Compute routing: one bounded Luna worker, followed by root corrections and
  final validation. OpenCode/Zhipu was not retried after the already-observed
  authentication failure. No external inference, private input or model install.
- Constitution and takeover governance gates passed on the final candidate.
  With all 13 report tasks succeeded and no active report task, the exact
  supervised Core child was stopped (4772; wrapper20588); supervisor19440
  restarted Core as28600. Health reports healthy/database ok. The supervisor,
  Ollama daemon, browser profiles and user configuration were not replaced.
- Existing CTH `brief-da1a713575104f419bcd8d8f644e2602` and BMP
  `brief-2386adfb508f40f6ba8a9280330be0ab` task results reopened through the
  live API after restart and matched saved artifact/source/business/multimodal
  values. This is persistence/compatibility proof, not final user acceptance.
