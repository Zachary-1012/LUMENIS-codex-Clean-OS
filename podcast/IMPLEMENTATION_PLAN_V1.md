# Podcast Module Implementation Plan V1

## Tonight's delivery target

Deliver a safe vertical slice, not a fake full platform:

`Podcast workspace shell → episode detail → persistent player → timeline markers → transcript seek → story/insight panel → evidence state → deterministic runtime metrics`

## Reuse map

- Reuse existing ZBC shell/navigation/layout tokens.
- Reuse existing database/migration mechanism.
- Reuse existing AI gateway and policy layer.
- Reuse existing logging/health/evidence primitives.
- Adapt WaveSurfer-style waveform behavior behind a local UI adapter; do not introduce a second player state machine.
- Adapt WhisperX/faster-whisper output into the canonical transcript contract.
- Adapt pyannote diarization behind `DiarizationProvider`.
- Study TranscriptDesk for waveform + transcript interaction and keyboard behavior.
- Study BBC React Transcript Editor for transcript/media synchronization concepts.
- Study Open Podcast analytics for cross-platform analytics data modeling.
- Study Rescript/CutScript for text-to-media editing concepts; do not import their entire app architecture.

## UX acceptance criteria

- One persistent player state within Podcast workspace.
- Click transcript sentence → seek player.
- Click timeline marker → open linked story/evidence.
- Click StoryNode → filter transcript and assets.
- Runtime visible at episode and segment level.
- AI suggestions visibly marked; verified evidence visually distinct.
- Mobile uses mini-player + bottom sheets; desktop uses two/three-pane workspace.
- Existing ZBC visual system remains authoritative.

## Data acceptance criteria

- Every imported item has source + observed_at + evidence_status.
- Every AI run has run_id/model/prompt/input hash/runtime/status.
- Metrics never mix platform denominators.
- Missing metrics remain null, not zero.
- No platform credentials/cookies stored in podcast domain tables.

## Verification gates

1. Schema validation.
2. Migration up/down or reversible migration test.
3. Unit tests for runtime calculations and timeline mapping.
4. Integration test for episode → transcript → segment → story relation.
5. UI smoke test for player/transcript synchronization.
6. Failure-path test: missing audio, missing transcript, failed AI, malformed timestamp.
7. Regression against existing ZBC routes.
8. Security scan for secrets and unsafe external fetches.
9. Evidence bundle before merge.

## Deferred until evidence exists

- Automatic publishing to platforms.
- Private platform scraping requiring credential/session handling.
- AI-only ranking of content quality.
- New database engine.
- Full waveform editor/export pipeline.
- Large-scale recommendation engine.
