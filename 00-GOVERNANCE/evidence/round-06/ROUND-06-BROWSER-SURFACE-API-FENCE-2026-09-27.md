# ROUND 06 — Browser Surface HTTP transport fence

Status: `SOURCE TESTED / REAL ACTOR E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser compatibility API
Base: `3ca66b3667fabbfb37daf7fa62a4ec0323156414`
Date: 2026-09-27

## Scope and decision

The old Browser Surface HTTP routes exposed low-level browser selectors and CDP
transport fields even though SYS-06 has no approved interactive viewport. The
route now requires a server-resolved active account session plus the existing
`SYSTEM/browser` read or write grant. It refuses all client `account` or `port`
selectors and uses only the verified product browser. JSON responses strip
CDP port, WebSocket URL, profile and acquisition-account fields. Internal
SYSTEM Browser functions and the approved collection identity owner remain
separate; no personal browser state was read or controlled.

## Verification

- Browser Surface, hybrid, downloads and AI Browser boundary suites: 78 passed,
  exit 0. Tests cover unauthenticated denial, forbidden collection-port input,
  verified product-session default, CDP field redaction and existing hybrid/
  download behavior without weakening the endpoint policy.
- `py_compile`, changed-path `git diff --check`, AI-native Constitution and
  Codex takeover governance validators passed at the current source snapshot.
- This is source/test evidence only. No real account login or Flutter page
  action used these routes. It is not a substitute for the SYS-06 real-user E2E.

## Remaining gate

The low-level routes still accept a client target identifier without proving
that it belongs to that exact actor and account session. They must not be
bound as a user-operable SYS-06 viewport/action API. The existing AI Browser
session API has an actor/session boundary but still lacks an approved frame/
action/result contract and canonical Source/Evidence return. The current
SYS-06 screen remains `DESIGN_EXPLORATION`; ROUND 06/14 remain `REWORK`.
