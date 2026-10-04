# Shared media workbench CI repair — 2026-10-05

## Scope

Commit `2738bbe5` bound the shared media workbench through a conditional export,
but omitted four required native implementation files from Git. GitHub App run
`37222362990` therefore failed before tests could compile because
`media_preview_native.dart` was absent from the checkout.

This repair adds only the missing native playback chain and its existing
targeted checks:

- a private temporary media-file lease and cleanup boundary;
- the native player adapter and lifecycle controller;
- the Windows/native preview widget;
- native/cache/controller/browser-preview tests; and
- one BMP-08 test correction that selects the real desktop Audio work area
  before asserting its `音频舞台` content.

The test correction preserves the capability requirement. The current desktop
studio presents Script and Audio as explicit work-area choices; the prior test
incorrectly asserted that the inactive Audio area was simultaneously visible.

## Local verification

At the staged source described above, the same default App command used by CI
completed successfully:

```text
flutter test
700 passed, 0 failed
```

This is local engineering evidence only. The native files handle authorized
returned artifact bytes; they do not establish a customer media task, actual
artifact playback, audition, Web/Android/macOS/Linux/iOS runtime behavior,
release or Product Owner acceptance.

## Publication state

This record is committed with the repair so an online reader can distinguish
the code fix from its later remote CI result. Remote App and Product workflow
verification is required after publication at the exact repair SHA.
