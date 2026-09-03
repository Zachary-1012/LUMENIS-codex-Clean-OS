# Podcast Module Research V1

## 1. Product hypothesis

The module is not a generic podcast player. It is a podcast intelligence and production system built around a reusable evidence chain:

`Person → Interview → Transcript → Story Node → Human Problem → Content Asset → Platform Observation → Audience Signal → Learning`

The research of mature interview IPs indicates that the durable asset is not episode count alone. It is the structured graph of people, stories, questions, conflicts, insights, runtimes, derivatives and audience responses.

## 2. Capability map

| Capability | First implementation | Reuse decision |
|---|---|---|
| Source/RSS ingestion | Adapter interface | Reuse existing collectors/config/logging primitives; add podcast adapter only |
| Audio/video normalization | FFmpeg adapter | Reuse system/runtime dependency if already present; otherwise optional dependency |
| ASR | Local model adapter | Reuse existing AI provider/runtime policy; prefer local/offline |
| Word timestamps | WhisperX/faster-whisper compatible adapter | ADAPT, keep provider-neutral contract |
| Speaker diarization | pyannote adapter | ADAPT; optional because model weights/licensing/runtime differ |
| Topic clustering | Embeddings + clustering | Reuse existing AI/embedding infrastructure where present |
| Story-node extraction | Structured LLM task | Reuse AI gateway; Shadow Mode first |
| Hook/title/clip candidates | Structured LLM task | Reuse AI gateway; never auto-publish |
| Platform observations | Evidence-first observation adapter | Reuse evidence/logging; no access-control bypass |
| Trend/runtime analysis | Deterministic analytics | Implement locally; no model required |
| IP knowledge graph | Relational entities + explicit relations | Extend existing DB/migrations, do not introduce another DB |
| Reports | Existing report engine where contract fits | Reuse/adapt |
| Notifications | Existing notification path | Reuse |

## 3. Open-source reference findings

### Speech-to-text + diarization

- `juhanimerilehto/whisper-ai-interview-transcription` demonstrates a local Whisper + pyannote interview pipeline with timestamps and JSON/Markdown/text outputs. Useful as a reference for the minimal local interview pipeline.
- `stephankostov/podcast-transcriber` demonstrates an end-to-end local pipeline: WhisperX, pyannote, topic generation, summarization, transcript UI and word-level seeking.
- `afeef/zabt-ai` demonstrates a production-oriented self-hosted architecture with faster-whisper, pyannote, queue/worker separation, object storage and OpenAI-compatible LLM endpoints. Its architecture is useful as a reference, not a drop-in dependency; license and infrastructure assumptions must be checked before reuse.
- `pyannote.audio` has moved forward to `community-1`; the current open-source model is explicitly positioned as an improvement over 3.1, especially for speaker assignment/counting. Treat model selection as a runtime capability, not a hard-coded business dependency.

## 4. Reuse policy

### ADOPT

Use an existing component when its license, runtime, security posture, data contract and platform constraints fit ZBC.

### ADAPT

Wrap or modify an existing component behind a ZBC-owned interface when it solves most of the problem but its public API, output schema or deployment assumptions do not fit.

### MONITOR

Keep a research record when a project is valuable but license, maturity, maintenance, resource cost or architectural coupling makes immediate adoption inappropriate.

### BUILD

Only implement new logic when no stable reusable component exists or when the business-specific layer is the differentiator: story-node ontology, interview scoring, content-yield metrics, cross-platform evidence model, IP graph and ZBC integration.

## 5. Podcast-specific intelligence metrics

- `story_node_density`: story nodes per minute.
- `emotion_peak_density`: detected emotional peaks per minute; AI-derived and non-authoritative.
- `insight_density`: insight candidates per minute; AI-derived.
- `question_quality_score`: structured assessment of specificity, openness, follow-up depth and answer yield.
- `interview_yield`: usable content assets produced per source interview.
- `interview_to_ip_conversion`: interviews that become durable series/assets/knowledge entities divided by total interviews.
- `content_asset_reuse_rate`: derivative assets reused across platforms/outputs.
- `runtime_retention_curve`: audience retention by runtime point where platform data is actually available.
- `platform_translation_delta`: performance difference between platform-specific packaging of the same underlying story node.

## 6. Required runtime/event model

Every processing run should carry:

`run_id, pipeline_version, model_name, model_version, prompt_version, input_hash, started_at, completed_at, duration_ms, status, evidence_ids, error_class`

Every metric observation should carry:

`platform, metric_name, value, observed_at, source_locator, evidence_status`

Never infer a platform metric from a different platform or from a later observation without marking it as derived.

## 7. Podcast content graph

`Person ──participates_in──> Interview`

`Interview ──contains──> Segment`

`Segment ──forms──> StoryNode`

`StoryNode ──addresses──> HumanProblem`

`StoryNode ──derives──> ContentAsset`

`ContentAsset ──published_as──> PlatformObservation`

`PlatformObservation ──produces──> AudienceSignal`

`AudienceSignal ──feeds──> LearningCase`

This graph should remain separate from ZBC brand-monitoring facts. Cross-domain links must be explicit and typed.

## 8. Engineering decision

Phase 1 should establish contracts, migrations, adapters and evidence storage without forcing a new UI or new database engine. Phase 2 adds local ASR/diarization as optional workers. Phase 3 adds story intelligence and benchmark analytics. Phase 4 adds platform-specific observation adapters and content production workflows.

The module must remain functional when AI is unavailable: ingestion, transcript import, deterministic runtime calculations, evidence storage and manual review must continue.
