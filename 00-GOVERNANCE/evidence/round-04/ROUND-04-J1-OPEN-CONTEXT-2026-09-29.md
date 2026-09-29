# J1 / ROUND 04 — open local viewing context

Status: **TESTED SOURCE + LOCAL API/CONTEXT FLOW VERIFIED; J1 PARTIAL; ROUND 04 REWORK**.
Base: `37b5cb4c449a79489421b08c477ccda29e948843`. Resolve publication from the
containing main commit; no whole-product or release acceptance is implied.

## Change and boundary

The Product Owner deferred product account design and requested an open local
product. The existing Permission owner now supports an explicit
`LUMENIS_OPEN_WORKSPACE=1` local read policy for subject_registry and
commercial_realtime_stream. It rejects non-loopback addresses, invalid Host or
Origin, forwarding headers, and requests carrying an account credential. Such
requests retain their existing Actor authorization. No Actor is fabricated and
the local path does not initialize account storage.

Context PUT/DELETE select/clear a stateless viewing scope; they do not write
settings, collect data or opt into AUTO. Their exact resolved route is removed
from the unrelated settings-write gate. Actual mutations keep existing fences.
The subject picker returns authorized CTH/BMP domains and registered names.
Default configuration remains off; the existing ignored local product .env was
backed up before enabling it. Windows user environment and Codex settings were
not changed. The service was restarted on loopback only.

## Current-snapshot verification

- 90 targeted Python tests passed, exit 0: local Permission policy, Context,
  Subject Registry, and app-level permission integration. An explicit disposable
  database seed was used. Tests include revoked configuration, credential-bearing
  denial, external Origin, cross-domain scope, no account initialization, and no
  registry/account writes from scope selection.
- Actual 8201 service health: healthy, database ok. Real Guangzhou Taikoo Hui,
  Shenzhen MixC Luohu, Nike and Le Labo all listed, selected, reopened with the
  same exact typed scope, and cleared to GLOBAL_ALL. A foreign-Origin focus
  request returned 401. No collection or business write was invoked.
- Independent frontend task reported actual narrow-screen browser
  GLOBAL → picker → search Guangzhou Taikoo Hui → focus header → clear → GLOBAL,
  without a login action. Its local screenshots are in
  `C:/Users/28049/AppData/Local/Temp/lumenis-cth03-20260929/`.
  This verifies selection UX only; frontend candidate files are not part of
  this backend commit.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: open the product and choose/clear a real work subject without product signup.
Entry: existing Web Workspace scope picker. Real input: registered production
subjects and brands. Result: correctly named CTH Subject or BMP BrandFocus,
restored by request headers, and a reliable return to GLOBAL. Failure/recovery:
invalid/unavailable scope stays explicit, stale credentials cannot fall back to
anonymous access, disabling the open policy immediately revokes that read path.

The CTH03 record stream still lacks its accepted scope/Evidence projection and
remains unavailable. A context selection is not a complete CTH/BMP business Job.
Full user result, analysis/action/evaluation and product-owner review remain open.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No production data or scope assignment changed. Global Commercial Coverage = NO /
NOT VERIFIED; Global Brand Coverage = NO / NOT VERIFIED; Guangzhou Taikoo Hui
Reference Coverage = PARTIAL; FULL_UNIVERSE_READY, RELEASED, OPERATING and
COMMERCIAL_READY remain NO.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT the existing local Permission/context owners to the current no-account
product decision. No auth framework, provider, store or architecture added.
COMMERCIAL OVERLAY IMPACT: this workstation read policy does not grant a remote
customer session, source license or external effect. Customer access design is
still deferred. Compute: bounded GPT-6 Luna Permission helper and tests; root
route integration/review/runtime probes; independent frontend selection E2E.
