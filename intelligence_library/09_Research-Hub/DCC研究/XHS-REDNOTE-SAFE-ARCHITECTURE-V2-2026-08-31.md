# XHS / RedNote Safe Architecture V2 — DCC Gate

Status: ACTIVE RESEARCH / AUTOMATION FROZEN

## Research-derived engineering patterns

Public RedNote/XHS MCP projects demonstrate persistent profiles, one-time manual login, cookie/storage reuse and explicit re-login flows. These patterns may be studied for reliability only. Stealth, fingerprint spoofing, human-behavior simulation, proxy rotation and other detection-evasion techniques are excluded.

Playwright documentation supports persistent profiles and authenticated state reuse; session storage has separate persistence semantics. Treat profile state as a security boundary and isolate it from test/worker state.

## DCC controls

ALLOW:
- browser lifecycle engineering
- persistent profile management
- session-state validation
- crash recovery
- explicit re-authentication UI
- official API/SDK research
- licensed provider evaluation
- user-controlled evidence workflows

BLOCK:
- automated browsing against the affected account
- repeated login probing
- stealth plugins/fingerprint spoofing
- behavior simulation intended to evade detection
- IP/proxy/device/account rotation for evasion
- private API reverse engineering
- signature recreation/request replay
- CAPTCHA bypass

## Two-browser policy

Primary: Chromium-based persistent browser.
Secondary: OS/system browser or WebKit/Safari handoff for compatibility.

The two routes must not be used to rotate identity or evade account controls. Do not copy cookies between engines.

## Gate

Any request to re-enable XHS/RedNote automation must fail closed until:
incident review -> authorization/rules check -> repository state agreement -> DCC audit -> regression evidence -> explicit user approval.
