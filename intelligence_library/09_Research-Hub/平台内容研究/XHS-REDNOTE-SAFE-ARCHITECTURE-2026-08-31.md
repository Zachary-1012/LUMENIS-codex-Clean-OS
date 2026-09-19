# XHS / RedNote Safe Architecture V2 — SICI Research Synthesis

## Findings

Public GitHub RedNote/XHS projects converge on persistent browser profiles, manual first login, cookie/storage persistence and explicit re-login. These are useful session-engineering patterns, not proof of platform safety.

Playwright recommends isolated test state and documents persistent profiles/authenticated state. Session storage is distinct from cookies/local storage and should not be assumed to persist automatically.

OWASP's anti-automation guidance confirms modern platforms can combine IP/network, session/identity, endpoint and behavioral signals. Therefore no single browser setting or IP strategy can be treated as a safety guarantee.

## Architecture decision

The system separates:

1. User-controlled browser shell.
2. Production collector workers.
3. Evidence ingestion.
4. Official/provider data sources.

The browser shell must not silently become a collector.

## Browser design

Primary: Chromium persistent profile.
Secondary: OS/system browser or WebKit/Safari handoff.

Both are independent. No cookie copying, identity rotation, or evasion behavior.

## Account incident

The affected XHS/RedNote account remains FROZEN for automation. It is not a test target.

## Research backlog

- official API scope monitoring
- provider provenance/cost/reliability comparison
- local browser lifecycle tests using synthetic fixtures
- evidence OCR quality tests
- session recovery tests without platform login probing
- multi-source provenance and conflict resolution

## Forbidden research translation

Do not turn anti-bot research into operational evasion code, stealth configuration, fingerprint spoofing, proxy rotation, or human-behavior simulation.
