# SYS-06 controlled reader source binding — 2026-10-05

## Purpose

The Product Owner reported that the product's supposed internal browser instead
redirected people into another browser. Source review found that SYS-06 had an
existing SYSTEM Browser API but was permanently removed from workspace routes
and replaced by an unavailable boundary. The former capacity panel could not
read an authorised page.

This batch binds the existing Browser owner to the shared Flutter Web
Workspace/Desktop/Mobile surfaces. Public Website remains explanatory, not a
browser-control surface. It does not create a WebView, copy a third-party
browser UI, open a personal browser, adopt a profile, or create a second
collector/Evidence/actor owner.

## Bound path

```text
SYS-06 workspace route
→ Sys06Screen
→ existing SYSTEM Browser API
→ existing permission/session owner
→ one server-owned controlled page
→ filtered target/revision-bound PNG frame
→ read-only product preview
→ explicit End session or Browser Back to the preserved originating task
```

The client sends no development Basic credential or business scope headers on
Browser API calls. The server accepts an anonymous product call only when it can
issue the fixed local-workspace principal on the configured loopback transport;
cookie, Authorization, forwarded and forged identity headers fail closed.

## Scope

- `ai_browser_api.py`, `ai_browser_runtime.py` and the existing Permission owner
  admit and isolate the server-issued `workspace:local` Browser principal.
- Flutter binary transport retains only the response metadata needed to verify a
  browser frame: media type, opaque frame/target IDs, revision, capture time and
  dimensions.
- `LumenisCoreClient` has an explicit Browser API path with no Core bootstrap
  credential or business context headers.
- SYS-06 has a localized Chinese/English/Korean reader surface. It opens only on
  an explicit action, accepts only `http`/`https` URLs without user info, keeps
  preview bytes in view memory, discards stale target/revision frames and stops
  a session only when the user explicitly asks.
- The route is a focused return layer. It does not discard the underlying
  workspace draft while the reader is open.

## Verification before publication

The following are source and isolated-widget/API checks at the local batch; they
do not prove a real permitted browser runtime or collection result.

```text
python -m pytest tests/test_ai_browser_default_engine.py tests/test_browser_e2e.py -q
17 passed

flutter test test/features/system/sys06_reader_test.dart
4 passed

flutter test test/navigation/lumenis_router_test.dart
15 passed

flutter test test/shell/lumenis_workspace_shell_test.dart
24 passed

flutter test test/core/lumenis_core_client_test.dart
10 passed
```

The browser-client test verifies that session/frame calls did not bootstrap
`/api/auth/config`, send Authorization, or send product context headers. The
reader tests cover normal frame display, URL refusal, stale-frame discard,
explicit stop, deep route entry, focus return and narrow/large-text layout.

## Published-source verification

GitHub `main` commit `154219a3df3a69af00097dbdbd135a165a9c9b77` is the remote
source containing this repair and its gate-alignment follow-up.

- [App Gate 37279577199](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37279577199)
  completed successfully. It passed the Experience gates, full Flutter analysis
  and the canonical Flutter test suite.
- [Product Gate 37279581122](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37279581122)
  completed successfully. It passed governance, contract, Experience,
  clean-checkout Python compilation, isolated database acceptance and the
  hermetic pytest suite.

Those online checks prove the exact published source can pass its required
repository gates. They do not promote the limits below to runtime or user proof.

## Limits retained

- No browser/CDP runtime was started for this batch.
- No social source, personal Mainland XHS account, Cookie, credential, page
  content, collection, Evidence admission or external effect was used.
- Page content remains a visual snapshot and is not a semantic accessible source
  representation, Canonical Evidence, Source admission or user-result proof.
- Real permitted URL navigation, expiry/revocation, capacity collision, desktop
  and mobile runtime, assistive technology, source return, recovery and Product
  Owner repeat operation remain `LIVE_NOT_VERIFIED` / open acceptance.

The current detailed contract is
`contracts/experience/screen-specifications/SYS-06.md`. It is implemented
source with acceptance still open, not a release or operating claim.
