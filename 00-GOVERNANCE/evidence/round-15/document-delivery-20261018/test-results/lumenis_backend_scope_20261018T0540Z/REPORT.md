# BMP backend read-transport candidate: isolated verification complete, integration open

## Delivered scope

The existing BMP scope owner now describes its successful local read admission with an additive `read_transport` field. Its original local-workspace policy, anonymous identity and false account-GLOBAL grant remain unchanged. It is not a sealed reports principal or Permission Evidence. Original permission code and guards are unchanged, and the existing route rechecks the binding after reading. Account paths never receive this local descriptor. BMP09 retains its independent reports/read authorization.

This self-contained snapshot has 3308 source files. Manifest SHA-256:
`5dec07f048bfa3c4569838e82413f4f48c8dcdb7e918572cc8d648d756b20789`.
Only `experience_runtime.py` and new `tests/test_bmp_local_read_transport.py` differ from 2248. No source was deleted. No GitHub, local computer, production DB, model, collection, paid resource or deployment action occurred.

## Final same-version verification

- Full original scoped regression plus new regression: 1934 passed, zero failed/errors/skips; 159.62 seconds. This is one final-version result, not an accumulation of historical test totals.
- 156 actual isolated HTTP requests: original SavedWork/SourceBrief prepare 11 + new-process cold 17; four-screen warm 64 + new-process cold 64. Valid local GLOBAL/FOCUS, account focus, hostile Host/Origin/proxy/Cookie, forged local labels, cross-domain/scope, reports-only revocation, account revoke/recover all behave as asserted.
- Two changed Python files compile; constitution gate passes. Ruff is unavailable in the existing environment; no dependency was installed or upgraded. Full lint is not claimed.
- Baseline and final source manifests were rechecked with no drift. Permission source is byte-identical to baseline. Network harness allows only loopback and blocks model imports; final denied network-attempt log is empty.

## Preserved failures

- The unchanged 2248 source fails all eight new local-descriptor positive cases because the descriptor is absent. Exact failure log is retained.
- First new fixture run: 11 failures/33 passes, caused by using BMP10's wrong binding field, Flask test client's dropped Cookie header, and wrong builder lookup patch target. The fixture now uses actual fields/transport/callers; all original safety assertions remain. Logs retain the failed attempt.
- First full run: 1933 passed/one failure because the external harness omitted `LUMENIS_VALIDATION_SOURCE_MANIFEST`. The original blocking scanner failed closed. No product/test source was changed to pass; exact manifest path and SHA were supplied and the entire 1934-test suite rerun. First failure remains in `results/full-first.*`.
- Historical 2248 parser/local failures, BMP04 double1.0 acceptance, older Experience failures and prior native crash are not rewritten by this backend result.

## Mainline preservation and remaining gates

The recorded current-main readback identifies `4dab98ed6357133da9307de846180ed4f7bba5f5`. This review independently reverified the retained official tree and all 3186 extracted main files: no byte/Git-blob mismatch. Main→2248 has 3008 unchanged, 178 modified, 121 added and zero missing extracted-manifest paths. The previously excluded `.env.example` also exists in 2248 and matches its official Git blob. See `MAINLINE_LINEAGE.json` for exact paths and evidence pins.

This proves file presence, not complete semantic preservation or acceptance of the 178/121 changes. Full delta adoption review and latest-main reconciliation remain blocking for formal integration. This snapshot is not a new product/mainline; no publication or merge is claimed.

The latest PO assigns frontend UI, Dart/model/parser and frontend tests to local Codex/GrokBot. The paused cloud Dart/UI changes are excluded from this snapshot and preserved separately as UNADOPTED, not a default merge recommendation. Current baseline Dart therefore still rejects the legal local responses; the original parser/count/date/UI gaps remain open. `LOCAL_CONSUMER_HANDOFF.md` gives exact backend consumption and negative-test requirements.

All original 19 open items, 195 G requirements, R01–R15/J1–J8/U01–U25, full research adoption and four-surface outcomes remain retained. Neither HTTP success nor these synthetic-input engineering tests establish real user, frontend, production, release or whole-product closure.

## Replay

`COMMANDS_REPLAY.sh` uses the existing validation venv and no installation. Copy into a fresh isolated root, update env.sh paths and keep the exact source manifest pin. Never replay writes into this frozen evidence directory. Runtime DBs, artifacts and temporary files are excluded from the distributable archive.
