# ROUND 06 — Browser frame paint readiness

Status: `SOURCE TESTED / REAL ISOLATED FRAME PROBE PASS / PRODUCT USER E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser AI Browser runtime/API
Browser source base: `6cf66ce8463a98effc99d05f806d6136f0c0a4ec`
Date: 2026-09-27

## Real defect and correction

The first public Bing frame immediately after successful navigation was a
4,580-byte, 1280 × 720 all-white PNG. Visual inspection confirmed that it was
not useful page content. The same isolated browser page rendered real content
later; a later frame had about 1.2 MB and was visually inspected.

`GET /api/browser/sessions/<id>/frame` now returns `202 BROWSER_FRAME_PENDING`
instead of a sparse early frame while the page paints. A bounded three-second
window then either serves a usable frame or returns an explicit
`503 BROWSER_FRAME_EMPTY` for still-sparse content. An intentionally empty
`about:blank` is exempt. The check uses page text and PNG sparsity as a
readiness heuristic; it is not semantic understanding of arbitrary webpages.
The UI must treat 202 as loading, never as a PNG or zero data.

## Verification and limits

- An isolated, disposable-DB Flask API probe with a test Actor/Permission
  stub navigated the real default Chrome engine to the public Bing page.
  Consecutive frame requests returned `202, 202, 202, 200`; the final PNG was
  1,244,111 bytes and had visible page content. The pre-existing verified
  browser process was preserved; only the probe context closed.
- 202 focused browser, security, verification, recovery, legacy-Evidence and
  injection tests passed with explicit disposable test seed. `py_compile`,
  Constitution Gate and Takeover Gate passed at the source snapshot.
- Sparse but legitimate pages may need a later product-specific readiness
  adjustment. A blank public page after the bounded window reports an explicit
  error; this Batch does not assert all sites render correctly. The real
  account/Permission path, SYS-06 UI polling and return, canonical Evidence,
  user review and ROUND 06/14 acceptance remain `REWORK / LIVE_NOT_VERIFIED`.
