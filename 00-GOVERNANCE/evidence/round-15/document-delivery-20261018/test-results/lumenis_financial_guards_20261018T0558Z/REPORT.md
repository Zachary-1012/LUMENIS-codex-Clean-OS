# Financial / MMM evidence guards

Status: isolated candidate, not integrated, not deployed, not product acceptance.

Baseline: `[LOCAL_WORKSPACE]/lumenis_bmp09_parser_20261017T2248Z/source` (frozen candidate). Current-main 4dab reconciliation remains separately required. `manifest.json` pins exact before/after bytes; `repair.patch` is the five-path integration diff. Only three original production owners plus two dedicated tests changed.

## Repairs

- `statistics_mmm.py`: raw-precision ArviZ summary (`round_to="none"`); exact expected scalar/vector parameter index coverage; reject duplicates/missing required diagnostics, nonnumeric/nonfinite diagnostics, each R-hat >1.05 or <=0 and ESS <200. Includes all channels, season elements and optional macro controls. Diagnostics retain explicit failure reasons; incomplete aggregate numbers are null, never a partial finite success. Original divergence gate, model, prior, holdout, controls and budget paths retained.
- `financial_tables.py`: current `thstrm_amount` binds only explicit `thstrm_dt`. `thstrm_add_amount` survives separately with exact JSON pointer and raw value, unknown dates and `ACCUMULATED_PERIOD_NOT_EXPLICIT`. No inferred fiscal start from report code; missing money is not zero. Existing regional parsing and provider errors retained.
- `financial.py`: exact normalized domain plus nonempty subject/brand comparisons prevent null equality from granting a match. Original name-candidate meaning remains not independently verified. Human-review save records a signed owner-specific Evidence receipt in the existing same transaction; binds actor/scope, artifact/hash, work/version/parent and full review hash (including evidence/source/selected spans). Typed read requires signed unique receipt from this owner/capture flow, current version, unchanged source and literal registry identity. Generic SavedWork still saves and reopens user payload but cannot upgrade it into authenticated human review. Existing unsigned reviews require explicit dedicated re-review; original files are preserved.

## Evidence

- `results/baseline-negative-regressions.log`: original candidate fails all three added financial regression cases: generic review forgery accepted; cumulative 900 labeled Q3; other subject admitted by null brand equality. Original diagnostic minimal counterexample retained at `[LOCAL_WORKSPACE]/lumenis_delta_audit_20261018/statistical_financial_pure_probe.log` (synthetic pandas table; no MCMC).
- `results/first-run.log`: first implementation run had the retained old test expecting the incorrect cumulative amount; changed assertion based on provider field semantics, not removed coverage.
- `results/final-run-1.log` through `final-run-3.log`: failed scope-test fixture setup retained. Real Permission rejected incomplete synthetic registry rows; final fixture keeps Permission on its real registered subject and injects anomalous owner-read rows only. No production permission change.
- `results/final.log` and `final.xml`: 81 passed, no skips (MMM guard tables, all regional financial tests, all public-financial pipeline tests). Includes legitimate review/save/replay/reopen/revoke, forged generic save rejection and signed-receipt tamper/recovery.
- `results/mmm-presampling.log` / XML: 10 passed, 44 deselected by explicit narrow MMM pre-sampling selection. Deselected tests are NOT_RUN, not passed. Actual CPU posterior tests explicitly excluded because sampling was not authorized for this repair.
- All five changed Python files compiled from their final bytes. Ruff NOT_RUN: no available binary in inspected environment; no installation attempted.
- Existing Python: `[LOCAL_WORKSPACE]/lumenis_restored_validation_20261017T2115Z/venv/bin/python`. `env.sh` isolates DB/artifacts/log/tmp/evidence; `run_tests.py` denies non-loopback networking and PyMC/PyTensor/model imports. Final network guard records no external attempts. Public transport fixture tests may use test-owned loopback; no real acquisition.

## Official semantics checked 2026-10-18

- OpenDART major-accounts developer guide: https://engopendart.fss.or.kr/guide/detail.do?apiGrpCd=DE003&apiId=AE00033 . Distinguishes current date/current amount and accumulated current amount; does not provide independent cumulative date field.
- ArviZ pinned-series documentation: https://python.arviz.org/en/v0.21.0/api/generated/arviz.summary.html . Installed ArviZ source `stats/stats.py:1552-1554` also confirms the literal string `none` disables rounding. Merely passing Python None would retain default rounding.

All provider test records are synthetic engineering fixtures, not retained live provider samples. Real OpenDART acquisition, real posterior sampling, business-data validation, frontend, production DB/runtime, full E2E, mainline CI and publication remain NOT_RUN / NOT_VERIFIED.
