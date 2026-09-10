# Git-readable package conversion v2

This directory closes the package-import ambiguity without touching product runtime code.

## What is complete

- `LUMENIS_CODEX_ZERO_DISCOVERY_FULL_PACKAGE_20260910.zip` content is represented in Git-readable handoff/execution files plus UTF-8 workbook CSVs.
- `LUMENIS_PRE_CODEX_FINAL_SUPPLEMENT_5_20260910.zip` contains five files that were hash-compared locally and are byte-identical to their same-name full-package counterparts; they are deduplicated rather than copied twice.
- The 13-sheet master workbook is represented as 12 direct CSV sheets plus `04_DB连接地图` in five ordered parts under `../../workbook-csv/parts/`.
- Current-truth corrections are kept separately in `../../EXTERNAL_TRUTH_SYNC_PATCH_20260910.md` and `../../execution/CURRENT_TRUTH_OVERRIDE_20260910.json` so historical source-package evidence is not silently rewritten.

## What is deliberately not claimed

The legacy `../text-packages/` Base64 manifest declared 13 full-package shards, but live GitHub verification did not find that full set online. It is now marked `DEPRECATED_INCOMPLETE_ARCHIVE_SHARDS`. Therefore **no byte-exact reconstruction claim is made for the old full ZIP archive**. This does not remove the Git-readable source-content conversion used by Codex.

## Codex / Doubao rule

Use `SOURCE_COVERAGE_MANIFEST.json` for import coverage, then obey the Current Truth Override. Do not restart five-repository discovery. `GIT-001` is closed/verified; the first executable cursor is `GIT-002`. Product readiness remains `NOT_READY` until the actual runtime/test/release gates pass.
