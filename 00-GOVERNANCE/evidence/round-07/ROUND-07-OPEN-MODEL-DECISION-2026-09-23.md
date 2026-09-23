# ROUND 07 — open-source-only model direction (2026-09-23)

Status: `PRODUCT OWNER DECISION / CANDIDATE NOT ACCEPTED`. This adapts the existing ROUND 07 and ROUND 15 AI gates; it adds no round, Gateway, database, Evidence or Permission owner.

## Product Owner correction and current truth

The Product Owner requires both local Codex assistance and LUMENIS product models to be freely available open-source models, without a hosted provider API key or per-call fee. This supersedes the earlier plan to keep Jev active for comparison. TypeSafe's [official API reference](https://docs.typesafe.ai/api) requires `Authorization: Bearer <API_KEY>` for `POST https://api.typesafe.ai/v1/systemone`; its [coding-agent guidance](https://docs.typesafe.ai/introduction/coding-agents) also says Jev is not a coding LLM. A free Jev tier could not be confirmed from official pricing material, and a free tier would still not meet the open-source requirement. Decision: `REJECT` Jev activation. No key should be requested, discovered for this purpose, or sent to the provider.

At the fresh 2026-09-23 check, local `HEAD`, fetched `origin/main` and live `refs/heads/main` were `19b461ddb9ecb37583003e471954e7716897a5e8`. Mainline has no accepted Jev adapter. The protected local Jev candidate remains default `OFF`; a host/redirect guard was merged only into that local candidate and passed 22 offline tests, but it is not product acceptance. Preserve its files for exact disposition; exclude them from product startup, routing, release and unrelated commits.

## Open-source candidate and self-developed route

The installed Ollama `qwen3.5:4b` artifact is `2a654d98e6fb`, 3.4 GB. Local `ollama show qwen3.5:4b --license` reports Apache License 2.0; the [Qwen official model card](https://huggingface.co/Qwen/Qwen3.5-4B) independently labels Qwen3.5-4B Apache-2.0. This is a **candidate** for the existing SYSTEM AI Gateway, not a selected production model or proof of a CTH/BMP user result. Local execution needs no hosted model key or per-call payment; hardware, electricity, distribution, support and operations still have costs. The already installed Ollama runtime remains the existing local execution route, not a new product owner.

The LUMENIS-specific self-developed capability should begin with the same appropriately licensed open-weight base and independently authorized LUMENIS inputs and human-verified labels. Version its prompts/adapters and, if justified by evaluation, tuned weights. Do not train on Jev output or proprietary material. Keep the base and adapted versions behind the one Gateway and compare them on the same authorized CTH/BMP/Shared jobs. An untrained adaptation reports `NOT_TRAINED / UNAVAILABLE`; a configured base model without a real result reports `LIVE_UNVERIFIED`, not `ACTIVE`.

## Remaining gates

1. ROUND 07: verify exact model revision, license/notice obligations and local capacity on each supported host; route through canonical Gateway, Permission and Evidence owners; return real result or honest unavailable/error/blocked state.
2. ROUND 07: define versioned typed-job schemas and an independently labeled real-work set. Measure accuracy, actual calibration or abstention (do not invent probabilities from raw model text), Chinese/English/Korean behavior where required, latency, failure recovery, trace and rollback for base and adapted versions.
3. ROUND 15: require real user-work E2E, human review, controlled promotion and rollback before product launch review. No model output may rewrite Evidence, Canonical Data, Permission, approval or effects.

The local Codex optional `qwen3.5:4b` profile is an engineering resource outside product source. Its CLI `READY` smoke succeeded, but it does not establish coding-task speed, model quality or LUMENIS product acceptance. The default Sol/Luna authority remains unchanged. Hosted CI and full user E2E remain separate blockers. Research accessed 2026-09-23; candidate license/maintenance and runtime must be rechecked at the pinned release before distribution.

## GitHub and official-model comparison

Read on 2026-09-23. Repository metadata was checked through GitHub's live API; a recent push shows maintenance activity, not model quality or release readiness.

| Candidate | Current source / license / maintenance | Decision for this workstation and product |
| --- | --- | --- |
| [Ollama](https://github.com/ollama/ollama) with [Qwen3.5:4B](https://huggingface.co/Qwen/Qwen3.5-4B) | Runtime MIT, pushed 2026-09-23; official Qwen weight card Apache-2.0, local artifact `2a654d98e6fb` is installed. Ollama's [structured-output contract](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx) supports JSON Schema through `format`. | **ADAPT** the existing SYSTEM Gateway/Ollama owner. Use a versioned typed schema plus independent validation and human review; JSON shape alone is not factual correctness or calibrated confidence. The 4B model is the only candidate here with a completed local Codex CLI smoke. Product real-job E2E remains missing. |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Official model card Apache-2.0; the [Ollama 7B package](https://ollama.com/library/qwen2.5-coder) is about 4.7 GB and coding-focused. It is not installed or benchmarked here. | **DEFER** as a possible Codex coding-quality challenger. Do not claim it is faster or better on this 16 GB CPU workstation without the same task/latency/memory benchmark; it is not the general CTH/BMP product model by default. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | MIT, pushed 2026-09-23; its [grammar support](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md) can constrain output. | **DEFER** an additional inference runtime while the existing Ollama owner satisfies the keyless candidate path. Use only if a measured gap justifies replacing or adapting that owner, never a parallel Production Truth. |
| [Hugging Face PEFT](https://github.com/huggingface/peft) | Apache-2.0, pushed 2026-09-23; parameter-efficient tuning is available. | **DEFER** weight tuning until authorized labeled data, a held-out evaluation set, and suitable compute exist. Versioned schemas, prompts and adapters can be developed first without pretending that a new model was trained. |
| [Qwen3-Coder](https://github.com/QwenLM/Qwen3-Coder) | Official GitHub repository describes 30B/Next/480B coding models; repository license metadata was not confirmed in this inspection. | **DEFER** on the present 16 GB host and do not import a large model merely for its headline benchmark. Reassess if target hardware and a pinned model license are proven. |

The practical current choice is the installed, Apache-2.0 Qwen3.5:4B through the already owned MIT Ollama runtime for **bounded local evaluation**. This is an inference from license, footprint, existing installation and one CLI smoke; it is not a comparative quality win or a product PASS. The eventual Codex/profile and product routing remain separate even if they use the same base weights.

A local keyless `/api/chat` call using a synthetic shopping-mall elevator issue, `think=false`, a required JSON Schema and `qwen3.5:4b` returned HTTP 200 and schema-valid `{route: commerce, abstain: true}` in 26.05 seconds (24 output tokens), process exit 0. The `abstain` flag means this example supplies no accepted routing decision. This proves only that the installed runtime can produce structured output without an external key; it does not prove calibrated uncertainty, correct business routing, Gateway binding, Permission/Evidence, throughput, real user work or release readiness.
