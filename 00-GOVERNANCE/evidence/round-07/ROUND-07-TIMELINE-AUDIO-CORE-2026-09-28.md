# ROUND 07 — bounded timeline audio core, 2026-09-28

Source base: `611dc0943943b29fed043b28e4af73ddf46e560e`.
Owner: existing Shared Content & Creation `video_editing.py`.
Scope: media stream inventory, local audio-only input, audio-track positioning and
stream selection, split/fade preservation, local demuxer/protocol restriction, and
typed model serialization. The protected local changes in the two owner files were
preserved and reconciled before this delivery; their prior copies are saved in the
private handoff directory. No new data, browser, Permission, API or UI owner.

Verification on the integrated repository source:

- `tests/test_video_editing_core.py`: 28 passed, no skips or thread leak; exit 0.
- A user-provided MP4 from the 12-source manifest was fingerprinted with real local
  FFprobe and its manifest SHA-256 matched. A muted video clip plus positioned,
  split and moved source audio retained gain and fades through JSON and typed model
  reconstruction. The source stayed unchanged; zero database opens; exit 0.
- `verify_ai_native_constitution.py`: PASS after source integration.
- The first real-media replay failed because the Root shell lacked the configured
  FFprobe path. Replaying the same source with the existing local FFprobe path
  passed; the initial failure is not counted as a pass.

The targeted regression and real-media proof establish the local timeline data
model only. Full untrusted project-document parsing, renderer and playable export,
Artifact reopen, exact-resource Permission, Evidence, UI, user review and real-user
E2E remain open under the same owner and ROUND 07/14–15. `ROUND 07=REWORK`;
`RELEASED=NO`, `OPERATING=NO`, `COMMERCIAL_READY=NO`.
