# ROUND 06 — approved HK worker and accurate login recovery

Base: `3f5c9b83b964c95e80c983eb4a8b95490c03adb2`. Existing SYSTEM Collector/Browser owners only.
GPT-6 Luna produced the isolated six-file candidate; root reviewed the exact
patch and confirmed no intervening main changes to those existing files.

## Fix

Explicit local endpoint 127.0.0.1:9223 is accepted only for the registered HK
identity/profile; 9222 and other local profiles remain forbidden. The worker
uses an existing context, verifies official-host self-navigation and session
presence, then creates its own page. No global target-reset/close happens
before verification. A missing optional identity Cookie no longer causes a
false mismatch. If present, that identity must agree; HK holder and SG data
residency are not conflated. Conflicting/wrong identities still fail closed.

Device-login limits and explicit re-login walls now propagate SESSION_EXPIRED
through worker/backend/adapter, separately from captcha and IP-risk states.

## Verification and real finding

- 66 focused regressions passed, exit 0, in the isolated worker candidate.
- Root parsed all six exact Python files successfully; Constitution Gate PASS.
- Actual registered local browser process/profile/port was verified. Existing
  RedNote self-navigation matched the allowlisted HK identity without Cookie
  export, profile rotation, or any Mainland-account access.
- One real Guangzhou Taikoo Hui search returned no records. The actual official
  page visibly reported a computer-device login limit requiring re-login.
  The old collector misread the login form's verification-code label as captcha.
- Root retained the page for user recovery. No retry loop, product DB write,
  authenticated data success, or anonymous/authenticated field parity claimed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: collect business evidence using the approved HK session and recover with
the correct action when its server session becomes unavailable. Entry: existing
worker/adapter. Real input: Guangzhou Taikoo Hui search. User-visible result:
SESSION_EXPIRED, not success or zero-valued business data. Successful ingestion,
Evidence/Canonical result and real-user E2E remain BLOCKED by platform re-login.
The user was asked to recover the approved HK session; other work continues.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT from current official
RedNote UI behavior and the existing browser owner. No dependency or new owner.
COMMERCIAL OVERLAY IMPACT: no rights, release, or operating promotion.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial/Brand NO / NOT VERIFIED,
Guangzhou PARTIAL; ROUND 06 REWORK; Full Universe/RELEASED/OPERATING/COMMERCIAL_READY NO.
