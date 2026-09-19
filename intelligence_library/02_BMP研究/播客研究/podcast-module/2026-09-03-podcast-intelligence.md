# Podcast Intelligence Research — 2026-09-03

## Scope

Research input for integrating a podcast module into Z-Brand-Core under Zachary OS AI governance. Focus: mature interview-IP reverse engineering, runtime analysis, cross-platform observations, content-asset reuse, IP/person/story graphs, and open-source speech/AI infrastructure.

## Mature-IP model distilled from research

`Person → Interview → Story → Human Problem → Asset → Platform → Audience Signal → Learning`

The durable asset is the structured corpus and graph, not merely episode count.

## OSS evidence

1. `juhanimerilehto/whisper-ai-interview-transcription`: local Whisper + pyannote interview transcription, speaker diarization, timestamps and structured output.
2. `stephankostov/podcast-transcriber`: WhisperX + pyannote + topic modelling + local LLM summarization, including word-level seeking and transcript UI.
3. `afeef/zabt-ai`: self-hosted production pattern using faster-whisper, pyannote, queue/worker separation, object storage and OpenAI-compatible LLMs. Treat as architecture reference; license is AGPL-3.0 and must be reviewed before any code reuse.
4. `pyannote.audio/community-1`: current open-source diarization direction with improved speaker assignment/counting compared with 3.1.

## Adoption decision

- ADOPT/REUSE: deterministic analytics patterns, provider-neutral transcript structures, evidence/run metadata patterns.
- ADAPT: ASR, diarization and topic-processing components behind ZBC-owned adapters.
- MONITOR: production architectures whose license/deployment assumptions do not fit ZBC.
- BUILD: podcast-specific ontology, story-node metrics, content-yield model, cross-platform observation schema, benchmark analysis and IP graph integration.

## Governance constraints

- Preserve ZBC architecture and frozen contracts.
- Reuse existing AI gateway and runtime policy; do not create a second general AI gateway.
- Local AI first; external providers optional.
- New AI behavior starts in Shadow Mode.
- No secrets, cookies, sessions or credentials in code/evidence.
- No access-control/CAPTCHA/rate-limit bypass.
- No claim of completion without test and evidence.

## Initial metrics

`story_node_density`, `emotion_peak_density`, `insight_density`, `question_quality_score`, `interview_yield`, `interview_to_ip_conversion`, `content_asset_reuse_rate`, `runtime_retention_curve`, `platform_translation_delta`.

## Engineering target

ZBC owns the business domain and persistence contracts. Zachary OS AI owns cross-repository governance, research evidence, capability registry and learning/contract synchronization. No direct cross-repository database access.
