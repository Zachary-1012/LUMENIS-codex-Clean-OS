# C4 — Windows media lease recovery fixture admission

> Status: **targeted Windows process/lease recovery verified; real media playback and user acceptance remain open.**
>
> Base: `dca16c30464757ef943b6e560904913851619cca`.

## Root cause and repair

The tracked test `app/test/features/shared/sh01/native_media_cache_termination_test.dart`
locates `app/test/fixtures/native_media_lease_child.dart`, but that helper was
an untracked local file. A clean checkout therefore could not execute the
tracked crash-recovery test.

The helper SHA-256 is
`274f9d5dfcd710d92a89a38ac0103f57c8c488fcae1d217e3e54c72faac24ded`.
It starts only on Windows, requires the test's explicit temporary root and
random nonce, validates the canonical parent/child path, creates a private test
lease, holds a lock, and exits abruptly only after the test sends its exact
command. The tracked test owns cleanup of that isolated temporary directory.
No product media, browser session, network endpoint or user file is opened.

The same workstation had a second local integration issue: Flutter 3.47.5's
ignored `.flutter-plugins-dependencies` metadata, regenerated at 19:42, omitted
the pinned `video_player` implementations even though `pubspec.yaml`,
`pubspec.lock` and `.dart_tool/package_config.json` still contained them. An
offline `flutter pub get` regenerated the metadata and restored the Windows and
macOS tracked plugin registrations to their mainline contents. Neither
`pubspec.yaml` nor `pubspec.lock` changed. Exact preimages are preserved outside
the repository at
`D:\LUMENIS_REBUILD\序\序境-convergence-backups\flutter-plugin-repair-20261005-1942`.

## Verification

- Flutter: 3.47.5, using the locked versions `video_player 2.14.0` and
  `video_player_win 3.3.0`.
- Offline dependency refresh: succeeded; locked dependency set unchanged.
- Command from `app/`:
  `flutter test test/features/shared/sh01/native_media_cache_termination_test.dart`
- Result: one Windows test passed, exit code 0. It confirmed a live lease is
  retained, then reclaimed only after the child exits abruptly.
- The fixture is admitted with this mainline change because the active tracked
  test directly requires it; it is removed from the protected-local-candidate
  list and retained as an admission receipt here.

This does not verify a real saved media artifact, native playback, audio review,
Web playback, other desktop/mobile targets, or Product Owner acceptance.
