# ROUND 06 — Local default-browser engine binding

Status: `LOCAL LIVE VERIFIED / PRODUCT E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser, with `cdp_helper.py` and `browser_surface.py` as compatibility callers
Base: `15a994bbf172a783b9b8dd2bf8a8d43359829fec`
Date: 2026-09-27

## Real user work and result

A desktop operator starts an authorized browser task from LUMENIS, sees its
page in the LUMENIS workspace, and returns to the source task with an Evidence
trace. This Batch verifies only the local engine prerequisite. The SYS-06
screen is still `DESIGN_EXPLORATION`, currently shows capacity rather than a
page viewport, and has no actor-to-browser-session binding. Its real user work
E2E, return path and product acceptance remain `REWORK / LIVE_NOT_VERIFIED`.

## Source change and boundaries

- Windows HTTPS association is read through the shell association API; the
  current host resolves to Chrome. Unsupported/default-unavailable engines
  fail explicitly instead of silently starting Edge.
- The existing general browser uses a separate, ignored `data/private`
  profile, headless mode and loopback CDP. Startup opens `about:blank`; page
  navigation still uses the existing browser policy. No Windows default or
  user-level model setting was changed. No personal Chrome or XHS profile was
  read, attached, migrated or automated.
- Port 9224 may be reused or stopped only when its browser identity matches
  the app-owned session marker and current CDP browser ID. Unknown occupation
  returns `UNVERIFIED_BROWSER_SESSION`; `force` cannot bypass it. The default
  no-account caller now selects this verified product session, not the
  acquisition session. The status API no longer returns the local profile path.
- This does not grant a Product Actor browser permission, authorize a source,
  bind a target to a user session, or produce Evidence/Canonical data.

## Verification at the source snapshot

- `.venv\Scripts\python.exe -m pytest -q tests/test_browser_surface.py --tb=short`:
  50 passed, exit 0. Tests include Chrome default selection, unsupported
  browser rejection, isolated/headless/loopback launch arguments, unknown
  session denial and browser API 403.
- Adding `tests/test_ai_browser_runtime.py` to that command gave 83 passed,
  exit 0. The affected hybrid and download suites initially exposed nine
  stale normal-path fixtures using the prohibited 9222/arbitrary ports. Their
  behavior assertions now use a mocked verified product session, with explicit
  9222/arbitrary-port denial assertions. The four affected suites now give
  102 passed, exit 0. This test migration preserves the same hybrid/download
  behavior and strengthens the identity boundary. The older
  `tests/test_browser_runtime_resident.py` cannot collect
  at current `main` because it imports the removed root `browser_runtime`
  module. That pre-existing compatibility-test migration remains a separate
  ROUND 06 gap; it was not deleted, quarantined or counted as PASS.
- `python -m py_compile cdp_helper.py browser_surface.py browser_surface_api.py`:
  exit 0. `git diff --check` for the changed source/test paths: exit 0.
- Actual local `.venv` runtime: default Chrome started in its isolated profile;
  strict-policy Bing navigation succeeded; CDP returned a nonempty screenshot
  and page title/URL; `Browser.close` succeeded and 9224 was closed. This was
  not a Flutter/SYS-06 user action or continuous operation test.
- The system Python lacks `websocket-client`, so its first stop probe could not
  close the browser; the product `.venv` has the declared dependency and closed
  it. The later complete `.venv` run ended with the port closed.

## Research and current-owner adoption

Accessed 2026-09-27: [Microsoft AssocQueryStringW](https://learn.microsoft.com/en-us/windows/win32/api/shlwapi/nf-shlwapi-assocquerystringw)
is the supported Windows association lookup (`ADOPT` for engine selection).
[Chrome remote debugging security change](https://developer.chrome.com/blog/remote-debugging-port)
requires a nonstandard `--user-data-dir` for modern Chrome (`ADOPT` as an
isolation constraint). Both map to the existing SYSTEM Browser caller/runtime;
neither is a Product Truth source or a second architecture.

Next existing ROUND 06/14 gates: exact Actor/Permission and target ownership;
safe Product Core browser API; `DESIGN_READY` SYS-06 viewport under the sole
Experience Constitution; page action/return/Evidence E2E on Desktop. Web and
Mobile must report the local browser capability unavailable rather than
simulate a desktop result. Global coverage and commercial readiness remain NO.
