# B01-B02 Source Mapping & Data Foundation Audit

Date: 2026-09-04
Status: ACTIVE / BUILD BASELINE
Scope: Z-Brand-Core production truth

## 1. Objective

Map the existing production implementation to the canonical UI/data/report specification without rewriting stable components. Establish one deterministic data path from external input to canonical data, visualization, UI, report and export.

## 2. Current verified source anchors

- `database.py`: production SQLite schema and additive migrations.
- `subject_rules.py`: canonical subject filtering boundary; must remain authoritative.
- `static/index.html`: production shell and current UI stylesheet composition.
- `export_report.py`: report aggregation/export path; currently contains report-side metric calculations that must be migrated to canonical metric functions.
- KOS engine/routes: existing KOS backend capability; reuse rather than duplicate.
- stability monitor: existing heartbeat/watchdog/health foundation.

## 3. B01 Source Map

| Build ID | Domain | Existing source | Decision |
|---|---|---|---|
| DATA-01 | Raw/DB | `database.py` | REUSE + EXTEND |
| DATA-02 | Subject filter | `subject_rules.py` | LOCK / SINGLE SOURCE |
| DATA-03 | Metric history | `metric_snapshots` in `database.py` | REUSE + ADD LINEAGE |
| DATA-04 | Import | `/api/local-import` path | HARDEN INTO UNIVERSAL INGESTION |
| DATA-05 | Report metrics | `export_report.py` | ADAPT TO CANONICAL METRICS |
| UI-01 | Global shell | `static/index.html` | REUSE, THEN CONSOLIDATE |
| UI-02 | Design tokens/components | `static/css/xujing-design-system.css` | AUTHORITATIVE TARGET |
| UI-03 | Historical CSS stack | multiple `/static/css/*.css` files | MAP, THEN RETIRE CONFLICTS |
| KOS-01 | KOS engine | `kos_engine.py` | REUSE |
| KOS-02 | KOS routes | `kos_routes.py` | REUSE + UI CONTRACT ALIGNMENT |
| HEALTH-01 | Runtime health | stability monitor | REUSE + DATA FRESHNESS |

## 4. B02 canonical data contract

All quantitative business data must follow:

External Input -> Parse/Extract -> Validate -> Normalize -> Function/Formula -> Canonical Dataset -> Visualization Adapter -> Table/Chart/UI -> Report/Export.

Pure evidence/assets may follow:

External Asset -> Evidence/Asset Store -> Linked Object.

Do not manufacture numerical data from non-numeric assets.

## 5. Required metric lineage

Every derived metric must be traceable through:

`metric_id -> formula_id/version -> calculation_version -> canonical dataset -> source record IDs -> raw/evidence IDs`.

A page, chart, report or export must not independently implement a second business formula.

## 6. Immediate P0 findings

1. Subject filtering must have one canonical rule source for Python and SQL.
2. Report/export calculations must consume canonical metrics rather than recalculate independently.
3. Time windows must use one shared inclusive/exclusive window implementation.
4. Existing `metric_snapshots` should be retained and extended with lineage/version metadata rather than replaced.
5. The import endpoint must become an ingestion pipeline, while preserving the existing upload behavior as an asset-ingestion fallback.
6. Frontend authentication fallback credentials must not be hardcoded in production client code; migrate to secure runtime configuration before release.
7. Canonical naming must be enforced from governance into UI/runtime strings.

## 7. UI B03 prerequisite

The current shell loads many historical CSS layers before the final Xujing design system. Do not remove them blindly. First generate a selector/component inventory, identify conflicts and migrate components to the authoritative token/component layer. Target architecture:

Global Shell -> Workspace -> Module -> Page -> Section -> Component -> Window -> Action.

## 8. Acceptance gates

A module is PASS only when:

- source path is mapped;
- reuse/modify/new decision is recorded;
- data source is canonical;
- formula/version is identified;
- table/chart/UI/report/export agree on the same golden dataset;
- evidence is traceable;
- loading/empty/error states exist;
- regression tests pass;
- commit and remote verification are recorded.

## 9. Non-negotiable governance

Prefer: REUSE -> ADAPT -> WRAP/ADAPTER -> ISOLATE -> NEW IMPLEMENTATION.

Do not change production truth directly from research output. Follow Contract -> Implementation -> Test -> Evidence -> Audit -> Release.
