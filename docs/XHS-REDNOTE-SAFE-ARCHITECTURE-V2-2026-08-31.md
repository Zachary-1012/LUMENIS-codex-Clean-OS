# XHS / RedNote Safe Architecture V2

> Status: ACTIVE RESEARCH / XHS AUTOMATION FROZEN
> Incident: XHS-SAFETY-2026-08-31-01

## 1. What the new research confirms

Public RedNote/XHS MCP projects show several reusable engineering patterns: persistent browser profiles, one-time manual login, cookie/storage reuse, explicit login commands, and browser lifecycle management. These patterns are useful for session reliability only. Anti-detection/stealth, fingerprint spoofing, human-behavior simulation, proxy rotation, or repeated login testing are not adopted.

Playwright's own guidance supports persistent authenticated state and isolated browser profiles. Authentication state may include cookies, local storage and IndexedDB; session storage has different persistence semantics. Browser state should be isolated per project/profile.

## 2. New architecture

User-controlled Browser Shell
  -> Persistent Profile Manager
  -> Local Session Validator
  -> Browser Health Monitor
  -> Explicit User Navigation
  -> Evidence Capture (optional)

Separate from:

Collector Workers
  -> Scheduler
  -> Platform Adapters
  -> Production Data Pipeline

The browser shell must never become an implicit production collector.

## 3. Browser reliability

Primary route:
- Chromium-based browser/profile.
- Dedicated persistent user-data directory.
- Explicit profile lock to prevent concurrent writers.
- Graceful close and crash recovery.
- Startup restores the profile and validates local state without probing login repeatedly.

Secondary route:
- OS/system browser handoff or WebKit/Safari on Apple platforms.
- Used for compatibility and user-controlled browsing only.
- Never used to rotate identity, evade controls, or copy cookies.

## 4. Session lifecycle

PROFILE_CREATED
 -> USER_LOGIN_REQUIRED
 -> USER_LOGIN_COMPLETE
 -> SESSION_STORED
 -> SESSION_VALIDATED
 -> USER_BROWSING

Invalid state:
SESSION_INVALID
 -> REAUTH_REQUIRED
 -> wait for explicit user action

Do not automatically submit login forms, repeatedly retry login, or treat a failed session as permission to create a new one.

## 5. Evidence pipeline

User-controlled public page
 -> screenshot/share/export
 -> evidence hash
 -> OCR/parse
 -> confidence score
 -> human validation
 -> SHADOW
 -> optional promotion after approval

Evidence must not overwrite Web/provider facts. Keep source, timestamp, raw reference, parsed value, confidence and verification status separately.

## 6. Data-source priority

1. Official API/SDK with actual authorized scope.
2. Licensed/contracted provider after source, legal, reliability and cost audit.
3. User-provided public evidence.
4. Existing XHS automation remains FROZEN.

## 7. Safety gates

BLOCKED:
- stealth/fingerprint spoofing
- human-behavior simulation intended to defeat detection
- IP/proxy rotation for evasion
- device/account rotation for evasion
- private API reverse engineering
- signature recreation/request replay
- CAPTCHA/verification bypass
- automated browsing/clicking/scrolling on the affected account
- repeated login probing

ALLOWED:
- browser lifecycle reliability
- profile persistence
- crash recovery
- session-state diagnostics
- official API research
- provider evaluation
- user-controlled evidence capture

## 8. Production decision

The affected XHS/RedNote account remains FROZEN. Do not use it as a test account for automation. Browser engineering can continue in an isolated local test environment using non-platform fixtures or an explicitly authorized test environment.

Recovery requires incident review, authorization/rule verification, three-repository state agreement, DCC audit, regression evidence, and explicit user approval.
