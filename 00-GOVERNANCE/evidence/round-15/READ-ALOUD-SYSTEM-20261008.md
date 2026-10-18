# System Read Aloud implementation evidence — 2026-10-08

## Scope and decision

Implement transient, user-initiated local system speech for text already visible in the existing LUMENIS product. Keep one shared Flutter service and the existing screen/data/permission owners. Do not send text or generated audio to a cloud/service, persist speech audio, write production data, or enable automatic playback. This record is implementation and targeted runtime evidence; it does not claim product-level SavedWork, podcast, video, or four-surface acceptance.

## Source changes

The shared read-aloud contract/service and platform adapters are in `app/lib/features/shared/read_aloud_{contract,backend,backend_stub,backend_io,backend_web,service,action}.dart`. Existing user-visible owners bind it to CTH-10 SourceBrief analysis, BMP-08 podcast script text, SH-01 video captions, and SH-04 a ready, reopenable artifact preview. Localized controls use the existing CTH/BMP/Shared copy registry for zh-CN, en, and ko.

The Windows adapter uses local SAPI voice tokens and their `Attributes\Language` values. A first runtime check exposed that reading `Language` from the token root returned no installed voices; reading the SAPI Attributes subkey fixed enumeration. Android uses only installed, non-network `TextToSpeech` voices and excludes voices marked `KEY_FEATURE_NOT_INSTALLED`. Apple platforms use the OS speech synthesizer with exact-language voice selection. Browser playback requires `SpeechSynthesisVoice.localService`. Linux has no native implementation and reports unsupported.

Platform operation is serialized in the existing service so stale speech requests cannot stop a newer request. Empty input stops any current voice and reports failure. Stop errors remain failures. Browser, Android and Apple callbacks update status only for the currently active utterance. No package or account was added.

## Research used

- [Android `Voice.isNetworkConnectionRequired`](https://developer.android.com/reference/android/speech/tts/Voice#isNetworkConnectionRequired()) — exclude network-dependent voices.
- [Android `TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED`](https://developer.android.com/reference/android/speech/tts/TextToSpeech.Engine#KEY_FEATURE_NOT_INSTALLED) — exclude voices whose local data is absent.
- [Apple `AVSpeechSynthesisVoice`](https://developer.apple.com/documentation/avfaudio/avspeechsynthesisvoice) — use the installed operating-system voice inventory.
- [MDN `SpeechSynthesisVoice.localService`](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService) — browser-side local-only filter.
- [Microsoft SAPI `ISpObjectTokenCategory`](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720754(v=vs.85)) — enumerate installed SAPI voice tokens.

These platform documents support adapter behavior only. They do not establish availability on a user's device or a completed LUMENIS business outcome.

## Verification

Observed on 2026-10-08 on the local Windows 11 workstation, Flutter 3.47.5 / Dart 3.13.4:

- `flutter build windows --debug --no-pub` — PASS. The first build encountered not-yet-generated Flutter ephemeral C++ wrapper sources; the normal Flutter build generation completed them and a subsequent build succeeded. No source cleanup was used.
- Isolated debug app launched with `LUMENIS_CORE_BASE_URL=http://127.0.0.1:1`, so no Core/API or DB operation was available. The temporary smoke entrypoint called the existing shared service against the real local Windows SAPI bridge. Output: `locales=[zh-CN, en-US]`, `beforeStop=playing`, `afterStop=stopped`. Hot restart repeated the same result. The temporary `app/lib/read_aloud_smoke_main.dart` was removed after this check.
- The initial implementation snapshot's `read_aloud_service_test.dart` run had 9 passing cases. The later status-truth correction and current regression totals are recorded below.
- `flutter analyze --no-pub` on the 12 changed product Dart files plus the service test — PASS, no issues. It was run via the existing temporary `R:` drive mapping because the Dart analysis server emitted malformed JSON for this workstation's Unicode `D:` path.
- DTD runtime diagnostics after hot restart — no runtime errors.
- Read-only host voice inventory found Windows zh-CN and en-US voices; no ko-KR voice. The real smoke did not request a missing Korean voice; exact-missing behavior is covered by the isolated service test.

## Follow-up: distinguish queued speech from audible playback

The platform `speak` call now means that the request was accepted, not that audio is already audible. Native `STARTING` and `PLAYING` acknowledgements are surfaced initially as `starting`; the service changes to `playing` only after `observe` confirms playback. Web speech returns `starting` after queueing and no longer infers playback from `speechSynthesis.speaking`; its current-utterance `onstart` callback is the start signal. The action remains stoppable while starting.

If playback remains `starting` for the bounded default 8-second window, the service requests stop and reports `failed`. The window is injectable for isolated tests. Added the localized `shared.read_aloud.status.starting` copy (`正在准备朗读…` / `Preparing to read aloud…` / `읽기 준비 중…`) and regenerated the Flutter copy map; locale registry counts are 823 each.

Current verification on 2026-10-08:

- `flutter analyze --no-pub lib/features/shared/read_aloud_contract.dart lib/features/shared/read_aloud_backend_io.dart lib/features/shared/read_aloud_backend_web.dart lib/features/shared/read_aloud_service.dart lib/features/shared/read_aloud_action.dart test/features/shared/read_aloud_service_test.dart` — PASS, no issues.
- `dart run tool/generate_lumenis_copy.dart` from `app/` — PASS; generated the localized copy map from all three source contracts.
- `flutter test --no-pub test/features/shared/read_aloud_service_test.dart test/features/bmp08/bmp08_studio_layout_test.dart test/features/shared/sh04/sh04_screen_test.dart test/features/shared/sh01/media_project_workbench_test.dart test/features/shared/sh01/sh01_screen_test.dart test/features/cth/cth10/source_brief_panel_test.dart` — PASS, 90 tests. The ReadAloud suite retains its original nine use cases and adds queued-but-not-playing, timeout-stop-fail, observation-confirmed-playing and stoppable/localized-starting cases. Full console log: `C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-read-aloud-final-tests-20261008.log`.
- `mcp__dart__dtd(listDtdUris)` found no running debug process or DTD instance. A hot reload of the changed source was therefore unavailable; no app was launched and no Windows rebuild was repeated for this follow-up. The earlier Windows SAPI smoke above remains evidence for its earlier source snapshot only, not for the new starting/playing UI transition.

## Required full-outcome acceptance remains open

| Acceptance path | Current evidence | Status |
|---|---|---|
| A. Authorized SavedWork/Brief button → real local speech → stop | CTH-10 has a SourceBrief action binding; unit/service and Windows adapter smoke pass. No authorized SavedWork/Brief record was opened through the real product flow. | OPEN |
| B. Podcast script at 0.75× → edit one sentence → new saved version read aloud, old session stops | BMP-08 is bound to visible script text. Widget/service test proves old scope stops and revised text starts at 0.75×. No persisted script-version/reopen flow was exercised and no real product UI audio session was run. | OPEN |
| C. Missing zh/en/ko local voice is honestly unavailable | Targeted service tests simulate each exact missing locale. Windows reports installed zh-CN/en-US only; Korean is absent and remains unavailable by exact locale matching. | PARTIAL — platform behavior verified on Windows for available locales; no real missing-Korean speak request or other platform runtime was exercised |
| Four-surface user operation | Windows debug smoke only. Web, Android, iOS and macOS runtime builds/voice behavior were not run. | OPEN |

## Limits

Android SDK is not installed on this workstation; iOS/macOS builds and device speech cannot be tested from this Windows host. Browser voice inventory and real browser playback were not tested. A standalone local service smoke is not a real customer Task, Permission, Evidence, SavedWork revision, user acceptance, release, or operating proof. Existing LUMENIS SavedWork authorization and persistence still need real end-to-end acceptance in the product UI.
