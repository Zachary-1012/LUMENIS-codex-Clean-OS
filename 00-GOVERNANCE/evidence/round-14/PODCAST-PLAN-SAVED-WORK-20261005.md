# Podcast plan to SavedWork binding — 2026-10-05

## Integrated normal path

The existing `podcast/intelligence/episode_runtime.py` now supplies the
structured `PodcastPlan` used by the existing Shared Timeline and SavedWork
owner. When a `podcast_episode` payload contains the new `podcast_plan` field,
SavedWork parses it before storing bytes. The plan preserves original and
corrected transcript text, speaker turns, chapter intent, opaque source
references, revision identity and explicit audio-stream selection.

The stored plan can derive a Shared Timeline, chapter document, editable script
and WebVTT transcript. The existing `/api/experience/saved-work` entry now
accepts the bounded `contract` field required by a podcast episode, so a
source-backed plan reaches SavedWork through its normal HTTP path, version
chain, reopen and revision protocol. Existing legacy podcast payloads remain
readable because validation is applied only when the new field is supplied.

## Verification

`58 passed, 2 skipped` targeted checks covered the podcast plan contract and
isolated SavedWork workflow. They include a source-backed plan save, fresh
reopen, parent-version revision and rejection of an invalid plan without an
Artifact side effect. The existing owner-route suite additionally verifies the
normal HTTP entry with a source citation, contract, save, reopen and revision.

## Limits still open

This is structured editable work, not a completed audio product. It does not
create, synthesize, mix, render, play or hear source audio; it does not prove
speaker/language/music-emotion quality, real customer material, actual media
Artifact bytes, four-surface playback, user review, release or operation. Those
remain the C4/C2/C6 user-outcome gates.
