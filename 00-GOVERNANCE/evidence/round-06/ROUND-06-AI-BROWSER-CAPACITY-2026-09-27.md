# ROUND 06 — Honest AI Browser single-session capacity

Status: `SOURCE TESTED / MULTI-THREAD PRODUCT E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser AI Browser runtime/API
Browser source base: `790303a6a130c7079118410baa1db3fbcf1aaf04`
Delivery parent: `bc546ef53156f9220a6b5b189fd4e9997157ac31`
Date: 2026-09-27

## Result

The actual local probe found that starting a second `sync_playwright` instance
on the same thread fails while the first one is active. The product API now
keeps one active session slot per process: the creating actor and login session
get their existing opaque session ID on repeat entry; another login receives
`409 BROWSER_CAPACITY_OCCUPIED`. It does not silently open a second context or
report a failed launch as success. The creation response no longer exposes CDP
port or headless implementation details.

## Verification and limits

- Focused AI Browser, security, action-verification, recovery, Evidence and
  injection suites passed at this source snapshot. Capacity tests check same
  login reuse, other-login conflict, denied personal port/profile and the
  absence of CDP fields in the response.
- `py_compile` and changed-path `git diff --check` passed.
- This makes the current capacity limit truthful. It does not solve cross-thread
  Playwright calls in a threaded server or demonstrate authenticated user work
  from SYS-06. The existing Browser owner must provide a serialized runtime
  execution path or equivalent within its current architecture before the
  viewport/action user E2E can pass. ROUND 06/14 remain `REWORK`.
