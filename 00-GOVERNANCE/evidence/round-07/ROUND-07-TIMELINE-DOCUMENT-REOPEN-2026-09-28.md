# ROUND 07 — bounded timeline document reopen

Date: 2026-09-28. Base main: `c997fb8f10ebc7a310e7ad6ceafb58b61efa2dbd`.
Owner: existing Shared Content & Creation `video_editing.py`.
This batch adds `Timeline.from_dict` for a saved edit document. It consumes
separately supplied typed MediaAssets, re-fingerprints actual local media, and
rejects malformed fields, injected source paths, false Evidence/rights claims,
missing files or stale bytes/duration/stream inventory. It returns freshly
fingerprinted assets. It does not resolve Artifact IDs or authorize source access.

Integrated current-snapshot proof:

- `tests/test_video_editing_core.py`: 43 passed, no skips, no thread leak; exit 0.
- One user-provided MP4 from the 12-source manifest was actually probed with
  FFprobe; the source SHA-256 matched the manifest. The saved timeline reopened
  through `Timeline.from_dict` with audio/video selections, split positions,
  gain/fades and version intact. Source bytes and mtime stayed unchanged;
  database opens 0; exit 0.
- `verify_ai_native_constitution.py`: PASS after source integration.

The parser validates local bytes at invocation time. The existing Artifact,
Permission, Evidence and renderer owners still must bind the authorized file and
recheck it when rendering. Export, playable film, UI and real user work E2E are
not accepted by this batch. `ROUND 07=REWORK`, `RELEASED=NO`, `OPERATING=NO`,
`COMMERCIAL_READY=NO`.
