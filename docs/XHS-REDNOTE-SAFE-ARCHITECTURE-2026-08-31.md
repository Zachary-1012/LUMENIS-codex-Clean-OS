# XHS / RedNote Safe Architecture V1

## Incident context

An XHS account received an explicit warning for suspected third-party tools/scripts automating browsing/viewing/publishing. Therefore all XHS/RedNote automation remains frozen.

## Research conclusion

Public GitHub projects demonstrate persistent Playwright sessions and browser automation, but those patterns must not be adopted as stealth or anti-detection mechanisms. The repository may study their session persistence, browser lifecycle, storage, observability, and failure recovery only.

## RedNote account

A user-owned RedNote account can currently browse/search but cannot like/comment/post. Treat this as an account state, not a permission to automate. No automated actions should be performed against it while the incident gate is active.

## Safe built-in browser architecture

The platform may provide a built-in browser shell for USER-CONTROLLED browsing only:

- Persistent profile/storage for legitimate session continuity.
- One-time manual login flow; never repeatedly probe login on startup.
- On startup: restore profile -> validate local session state -> open a neutral local landing page -> wait for explicit user action.
- If session is invalid/expired, show `SESSION_REAUTH_REQUIRED`; do not auto-submit credentials or repeatedly retry.
- Preserve cookies/local storage only within the dedicated browser profile and encrypt/secure local secrets where supported.
- Keep browser profile isolated from automation workers and data collectors.
- Provide clear `SIGNED_IN / SESSION_UNKNOWN / REAUTH_REQUIRED / BLOCKED` states.

## Two-browser strategy

Use two independent browser engines/hosts only for resilience and compatibility, not for evading platform controls:

1. Chromium-based embedded/desktop browser for the primary built-in browser experience.
2. OS/system browser handoff (or WebKit/Safari on Apple platforms) as a secondary user-controlled route.

Do not rotate between them to evade account controls. Do not copy session cookies between engines.

## Data collection alternatives

Priority order:

1. Official API/SDK when the required scope is actually authorized.
2. Licensed/contracted third-party data provider after legal/data-source audit.
3. User-provided public evidence (screenshot/share/export) -> OCR/parse -> validation -> Shadow.
4. Existing XHS automation: FROZEN.

## Explicitly prohibited

- Human-behavior simulation intended to defeat detection.
- Stealth plugins/fingerprint spoofing.
- IP/proxy rotation for evasion.
- Device/account rotation for evasion.
- Private API reverse engineering.
- Signature recreation or request replay.
- CAPTCHA/verification bypass.
- Automated browsing/scrolling/clicking against the affected account.
- Repeated login testing.

## Recovery gate

No XHS/RedNote automation may be restored until the account incident is reviewed, the applicable platform rules/authorization are verified, all three repositories agree on the state, DCC approves the change, and the user explicitly approves restoration.
