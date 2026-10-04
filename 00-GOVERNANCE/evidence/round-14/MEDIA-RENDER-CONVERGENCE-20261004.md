# Existing media renderer convergence — 2026-10-04

This is scoped implementation evidence under the approved product blueprint.
It is not C4 acceptance, a finished customer film, or a listening review.

## Adopted implementation

The retained local `lumenis/shared/content_creation/rendering.py` changes now
enter the existing Shared renderer used by
`shared_artifacts.py:stage_timeline_artifact` through `render_timeline` (the exact
caller remains authoritative; no parallel export service is added).

- Centre a dissolve on the existing cut using actual incoming/outgoing handles.
  Preserve the total timeline length and unrelated clip boundaries. Reject
  insufficient handles, subframe windows, overlapping windows, reversed/nonadjacent
  clips and unsupported effects before starting the encoder.
- Mix the audio through the existing audio path. Video transitions do not silently
  become audio crossfades. Keep captions and separate output verification.
- Preserve a cancellation/Permission callback's original error identity, including
  callbacks raising OS/process exception subclasses; reap the encoder before
  cleaning private temporary files.
- Continue current fresh Permission checks, source fingerprint verification,
  Artifact integrity, parent versions and demo/rights boundaries. No new source
  rights or publication permission is inferred.

## Research adaptation and actual verification

[FFmpeg's official xfade contract](https://ffmpeg.org/ffmpeg-filters.html#xfade),
read 2026-10-04, requires compatible constant-rate inputs and matching dimensions,
pixel format, frame rate and timebase. The existing segment normalization and
explicit `settb` preserve that requirement. The editing decision here uses real
handles and a fixed cut position; it does not shorten the work to fit a transition.
This absorbs an audiovisual continuity principle into the current renderer.

The affected checks were executed with the installed FFmpeg/ffprobe and an
isolated test database:

| Check | Actual result |
| --- | --- |
| Timeline rendering | 79 passed, including three real colour-frame dissolve/mixed-cut exports, actual caption export/reopen, audio packet preservation, literal captions and cancellation/reaping |
| Audio timeline | 8 passed |
| Artifact storage/listing/read integrity | 55 passed |
| Retained PodcastPlan | 19 passed locally, but this separate plan is not published by this renderer batch or claimed bound to the product |

The first invocation put pytest outputs outside the required private temporary
root; 33 checks correctly rejected that location. The runner was corrected to a
named directory under the user's Temp; no output-path restriction was weakened.
All subsequent checks above completed successfully. These controlled synthetic
media inputs are engineering verification, not real customer outcomes.

`shared_artifacts.py` and `video_editing.py` were byte-compared with published
main (line-ending normalization only) and matched. Relevant XML/argv/exit logs
are in `D:/LUMENIS_REBUILD/序/序境-convergence-backups/direct-repair-20261004-202614/`:
`media-private-temp.xml`, `media-artifact-owner.xml` and matching JSON/log files.

## Still open

Actual customer media, normal admitted Source/Artifact rights, real UI operation,
native/audio playback, all required language listening, newly loaded production
runtime and complete four-surface acceptance remain separate requirements.
Keep the useful retained PodcastPlan/native-player/collection work protected until
its actual caller and complete normal path are integrated. No paid GPU/model or
other window was started in this batch.
