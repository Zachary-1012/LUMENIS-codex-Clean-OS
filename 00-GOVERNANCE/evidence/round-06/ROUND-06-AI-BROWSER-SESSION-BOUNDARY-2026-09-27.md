# ROUND 06 — AI Browser session boundary on the default engine

Status: `LOCAL LIVE VERIFIED FOR ONE SESSION / PRODUCT E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser and AI Browser compatibility API/runtime
Base: `b20b65874802b974594af86733515a9c25bfc606`
Date: 2026-09-27

## Real user work and scope

An authorized desktop operator requests a controlled browser session, opens an
allowed source, observes the result and returns to the task with Evidence. This
Batch closes the old AI Browser runtime's unsafe browser-selection path. It does
not claim the SYS-06 user interface, real login, multi-user operation or the
Source → Evidence → Canonical product task has passed.

## Source behavior

- The AI Browser API rejects caller-selected CDP ports, visible-browser mode and
  caller profile paths before creating a session. Direct manager/runtime callers
  have the same fail-closed boundary.
- Runtime startup reuses only the verified, isolated Windows default-browser
  instance on 9224. It no longer attaches an arbitrary occupied port, chooses
  the first existing tab, or launches a separate bundled Chromium profile.
  Each started session creates its own Playwright browser context and page.
- Every AI Browser API request requires a real account session and an active
  `SYSTEM/browser` read or write grant. Session reads, actions, stop and Evidence
  are bound to the creating actor **and** account session. A failed automatic
  start returns 503 and removes the failed session instead of reporting success.
- Direct navigation uses the existing Browser Surface policy. A `file:` URL is
  denied before `page.goto`. No Cookie or personal browser profile is read.
- The former `tests/test_browser_e2e.py` executed a 9222 connection at import
  time and contained no acceptance assertions. Its active entry has been
  replaced with a blocking regression that denies 9222 in both product and AI
  Browser paths. The historical script remains retrievable from the base Git
  commit; this is an identity-safety correction, not a claim of user E2E.

## Verification

- `.venv` Playwright version: 1.63.0; repository declares `playwright>=1.30.0`.
  [Official CDP connection](https://playwright.dev/python/docs/api/class-browsertype)
  and [isolated contexts](https://playwright.dev/python/docs/api/class-browsercontext)
  support the `connect_over_cdp` → `new_context` → `new_page` binding used here.
- Focused AI Browser, security, action-verification, recovery, Evidence and
  injection tests: 198 passed, exit 0. They include denied personal
  port/profile, unavailable start,
  actor/grant denial, login-bound session visibility and blocked navigation.
- `py_compile` and changed-path `git diff --check` passed.
- Real local `.venv` probe with an isolated disposable DB: the approved default
  browser started; an AI Browser session navigated to public Bing with result
  `PASS`, nonempty title and a legacy BrowserEvidenceStore record ID; the
  session and verified general browser closed, and port 9224 was closed. This
  was direct runtime execution,
  not an authenticated HTTP/UI user E2E.
- A second concurrent `sync_playwright` instance on the same thread failed with
  Playwright's asyncio-loop error. Multi-session operation remains `REWORK`;
  no multi-user acceptance is claimed. A first disposable-DB probe also exited
  nonzero only during Windows temporary-file cleanup after the browser work had
  completed; a later direct runtime probe exited zero. The temporary probe
  directories are outside the product workspace.

## Remaining existing gates

The old Browser Surface API still exposes low-level CDP details and lacks an
Actor/target binding, so SYS-06 must not attach to it directly. The new AI
Browser API needs authenticated real-user HTTP E2E and a safe page viewport/
input contract; the SYS-06 spec is still `DESIGN_EXPLORATION`. The legacy
BrowserEvidenceStore ID is not canonical Source/Evidence lineage. Browser
actions must enter canonical acquisition and Evidence/Permission when used for
business work. ROUND 06/14 remain `REWORK`; release and operating proof remain NO.
