# Shared media workbench integration — 2026-10-05

This delivery integrates existing Shared media workbench source into the single
Flutter product. It is engineering evidence for an existing capability, not C4
real-user acceptance, a claim of a completed customer film/podcast, or a release.

## Integrated behavior

`SH-01` retrieves an already saved authorized content-project version, renders it
in the correct target player and connects its playhead to the shared timeline only
while that exact saved version still matches the current draft.

- Windows writes authorized MP4/WAV bytes into a verified private temporary lease,
  opens the existing `video_player` adapter, supports play/pause/replay, mute and
  seek, pauses on cover/inactive state, releases the native player and deletes the
  lease after close.
- Web uses an HTML `<video>` or `<audio>` element only for authorized returned
  bytes. A queued seek waits for `loadedmetadata`, then reports the actual decoded
  position back to the timeline. Remote source URLs, transport credentials and
  media-platform sessions never reach the element.
- Desktop/mobile workbench layouts retain source import confirmation, scope
  quarantine, version/reopen, editing, cancellation/leave protection, horizontal
  panning/zoom, keyboard timeline seek, previous-render distinction and recovery
  from retrieval or player failures.
- The podcast studio uses task-specific desktop/mobile arrangements, accessible
  controls and real empty/unavailable states; it does not fabricate waveform,
  transcription, synthesis, audio or model results.

When a user edits a draft after loading an exported version, timeline events no
longer change the playhead of that older media. Timeline keyboard semantics now
always declare its current, incremented and decremented time values.

## Verification

- 86 Flutter unit/widget/recovery checks passed across SH-01 workbench, Windows
  preview/cache/controller, BMP-08 and launch surfaces.
- A Windows release build completed at 2026-10-05 01:42 China time. The artifact
  includes `video_player_win_plugin.dll`; the generated runner registers
  `VideoPlayerWinPluginCApi`.
- The direct Windows adapter and browser byte-player are source/fixture verified.
  The browser test server in Flutter 3.47 on Windows returns 404 for its own
  CanvasKit path after converting the path separator. Both CanvasKit and Skwasm
  browser test attempts stopped at suite load, before application test code
  executed. The product source was not changed to suppress the test. The known
  Flutter issue and installed SDK resource evidence are preserved outside this
  repository's source tree.

## Limits still open

No actual customer source/Brief/Evidence/Permission/Artifact task was run in the
new Windows or Web build. Native playback of a real saved artifact, audio hearing
review, a Web Workspace browser E2E, Android/macOS/Linux/iOS runtime, release
packaging notices and Product Owner repeated acceptance remain separate required
evidence. A successful compilation or fixture test does not change those states.
