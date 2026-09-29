# J5/J6 — bounded existing Timeline renderer integration

Status: **ENGINEERING TESTED; PRODUCT UI/API INTEGRATION NOT YET ACCEPTED**.
This does not complete J4 general creation, J5 video, J6 podcast or ROUND 07.

Root reviewed and selected exactly three frozen candidate paths:
`lumenis/shared/content_creation/rendering.py`, `tests/test_timeline_rendering.py`,
and `tests/test_audio_timeline_rendering.py`. The existing Timeline/source models
are unchanged. Renderer SHA-256:
`9954bafc89053c2513a825878feac7ba14f7f12152442982ec87d3d86d3f3102`.

The renderer supports contiguous multi-clip video, selected audio streams,
independent audio placement/gain/fades, audio-only WAV, explicit voiceover-driven
music ducking, pre-encode sample-peak limiting and measured final-file loudness.
Source identity is rechecked, output timing/frame/codec/stream shape is verified,
and Permission revocation callbacks stop/reap the encoder. Non-cut transitions,
overlays and unsupported track shapes fail explicitly. This is neither automatic
source separation nor a guarantee of final true-peak/channel mastering quality.

## Current main verification

- Initial root test run: 21 passed and 14 skipped because process-local FFmpeg
  paths were absent. This was not renderer acceptance.
- Reused the candidate's verified development-only FFmpeg/FFprobe 9.0.2 binary
  with process-local paths only: **35 tests passed, zero skips, exit 0**.
  Real encoded synthetic signals verified duration, frame boundaries, audio
  offsets, selected stream/gain, multiple music stems, ducking recovery,
  loudness semantics and interruption cleanup. They are engineering inputs,
  not the user's finished video/podcast.
- Existing `test_video_editing_core.py` and `test_shared_artifact_flow.py`
  regressions passed, exit 0; Constitution gate passed after integration.
- No persistent PATH, media provider, production DB or account configuration
  changed. The portable GPLv3 development binary is not automatically approved
  for redistribution with the product.

The historical isolated candidate's licensed-media run remains distinct from
main acceptance: its full source-import/Artifact/project route is not yet merged.
Do not claim the renderer alone supplies the UI export/reopen workflow.

## Unexpected publication and disposition

The old in-product version watcher automatically committed/pushed the three
selected files plus a frontend SH-01 specification candidate in `06d156c7`
before root finished verification/publication. Root preserved all history and
work, disabled the actual version-center auto_commit/auto_push configuration,
and initiated the default-off regression fix. This commit proves source presence,
not completed review. The renderer tests above were subsequently completed on
the exact copied hash. SH-01 retains only its explicitly reviewed presentation
scope; automatic saving does not promote the full screen to DESIGN_READY.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: edit real media into a new reusable video or audio program. The completed
increment is the existing renderer's tested encoding capability. Main still needs
the scoped source-import/project API, approval/Artifact binding, frontend controls,
actual user-media creation, reopen/revise and in-job recovery acceptance.
J5/J6 remain REWORK / LIVE_NOT_VERIFIED. Evidence here must not substitute for
their finished programs or J4's original client deliverable.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: adapt mature FFmpeg behavior
inside the existing owner as documented in the whole-product research plan;
no second media system. COMMERCIAL OVERLAY IMPACT: source rights and binary
distribution obligations remain separate from successful encoding.
