# ROUND 06 — Authorized internal browser frame contract

Status: `SOURCE TESTED / ISOLATED ENGINE HTTP PROBE PASS / REAL USER E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser AI Browser runtime/API
Browser source base: `6a23ddc4a17d4680658c0c7f209267f47a6029ec`
Date: 2026-09-27

## Result

The existing actor/account-session and SYSTEM/browser Permission gate now serves
`GET /api/browser/sessions/<session_id>/frame` from that login's active isolated
page. A successful response is uncached PNG with opaque frame and target IDs,
page revision, UTC capture time and actual image dimensions. The session create
and status responses expose the verified engine label, safe title/address,
current target and revision, and only the navigation, reload and frame actions
currently advertised to the first UI binding. URL display drops credentials,
query and fragment. Navigation/action responses include the new page revision,
so the future UI can discard a late frame from an older revision or target.
No native browser chrome, CDP port or profile is returned to the UI.

## Verification

- 201 focused browser/security/action/recovery/legacy-Evidence/injection tests
  passed using an explicit disposable `LUMENIS_TEST_SEED_DB`; no daemon thread
  leak was reported. The protected repository DB had WAL/SHM sidecars, so its
  pytest seed gate correctly refused an incomplete main-file copy. No sidecar
  or protected DB was changed to make tests pass.
- `py_compile`, changed-file whitespace check, Constitution Gate and Takeover
  Gate passed at the current source snapshot.
- A real isolated default Chrome engine, disposable DB and Flask API probe
  with a test Actor/Permission stub returned navigation `success=true` and a
  PNG frame of 1280 × 720 pixels. The create, navigation, status and frame
  target/revision fields matched. The existing verified browser process was
  preserved; only the probe context was closed. No personal XHS identity was
  used.

## Remaining acceptance

The test Actor/Permission stub is not a real product login. Raw page pixels
are untrusted external content and do not become canonical Evidence. The UI
must reject late frames by target and revision, and must not infer back,
coordinate click or other capabilities from icons. `SYS-06` is still
`DESIGN_EXPLORATION`; its approved UI binding, real Actor/session E2E, target
and effect checks for interaction, user review and ROUND 06/14 acceptance remain
`REWORK / LIVE_NOT_VERIFIED`.
