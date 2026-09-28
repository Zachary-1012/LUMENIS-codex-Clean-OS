# ROUND 07 — real single-clip local render

Status: TESTED SOURCE + REAL MEDIA TRANSFORM / ROUND 07 REWORK.

Base `0576ce971dccaef5047ed4765f441222b3654716`; Sol integrated the Shared Content & Creation renderer into current main without modifying the accepted Timeline model or the protected local candidates. The renderer takes exactly one video clip, validates the saved asset fingerprint and supported edit state, and emits a new private temporary MP4. It supports source trim, selected original audio or mute, gain and fades; unsupported tracks, overlays and transitions fail explicitly. It does not authorize export, register an Artifact, use a database, or publish media. Rights remain unknown.

Current integrated snapshot: 18 targeted renderer tests PASS on an explicit disposable DB seed, including actual FFmpeg audio-offset regressions. Sol independently reran `verify_real_render.py` against the original user-provided MP4 in the 12-source manifest. The 1–3 second selection produced two actual 2.000-second MP4 files, each with 60 decoded frames, with respectively one and zero audio streams. Source digest, size and mtime were unchanged; database open attempts were zero. Root receipt: `C:\Users\28049\AppData\Local\Temp\lumenis-root-real-render-20260928.json`. No fixture substitutes for this media result.

Still open: Artifact lookup, source rights and Permission/effect authorization, Evidence binding, approved export/download, reopen after render, product UI, user review, evaluation and real user-work E2E. Multi-clip and additional-track rendering remain unsupported. No ROUND 07 exit, release or operating claim follows.
