# XHS / RedNote Browser Gate

## Purpose

Improve built-in browser reliability and session persistence without implementing anti-detection or platform-control evasion.

## Allowed

- Persistent user-owned browser profile.
- Manual one-time login and local session restoration.
- Startup session-state validation without repeated login attempts.
- Clear re-authentication state when the session is genuinely invalid.
- Browser crash recovery and profile backup/restore.
- Primary Chromium route plus secondary OS/WebKit browser handoff for user-controlled browsing.
- Observability: browser version, profile version, startup reason, session state, crash reason.

## Blocked

- Stealth/fingerprint spoofing.
- Human-behavior simulation to defeat detection.
- IP/proxy rotation for evasion.
- Account/device rotation.
- Private API/signature reverse engineering.
- CAPTCHA/verification bypass.
- Automated browsing against the incident-affected account.

## State machine

`PROFILE_RESTORE -> SESSION_VALIDATED -> USER_CONTROLLED_BROWSING`

or

`PROFILE_RESTORE -> SESSION_REAUTH_REQUIRED -> USER_MANUAL_LOGIN -> SESSION_VALIDATED`

Never use startup probing as a login-health test loop.
