# SYS-08 — Observability and logs

```yaml
screen_id: SYS-08
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Observability
binding_ids:
  - BACKEND-GAP-043
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: trace waterfall/log/error separation, safe observability and §36 acceptance.
- Product contract: operational logs remain distinct from frontend logs, Evidence and business truth.
- References: `KEEP_AS_EXPLORATION`; no generic monitoring dashboard is authoritative.
- Anti-template check: inventory, trace boundary and structured records are intentionally separate; no unsupported time-series chart.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator permitted to read a sanitized observability summary.
- Real task: understand whether logs/trace records are available without exposing credentials, sessions or absolute paths.
- Completion signal: real returned inventory/records display; absent trace remains unavailable.
- Out of scope: arbitrary log download, destructive cleanup, credential inspection, path disclosure and fabricated throughput/error-rate metrics.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-08` → `experience_screens._build_sys08()` → `logger.get_log_summary()`.
- Current backend returns sanitized filename/count summary only; no verified Trace waterfall or user-scoped log permission is present.
- Return: originating SYSTEM route; no export route is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing/safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Total files/size | KPI ids `sys08.files`, `sys08.size_mb` | Ready numeric only; offline/null is unavailable | BACKEND-GAP-043; `logger.py`; `sys08_snapshot.dart` |
| P1 | Filename/modified summary | table rows `文件/大小MB/修改` | Path-like values are redacted; file content is never shown | Current SYS-08 builder |
| P0 | Structured records | No current builder records | Empty state; no synthetic rows | SYSTEM Observability |
| P0 | Trace waterfall | No current callable | Explicit unavailable; do not draw chart | BACKEND-GAP-043 |

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | summary pending | Wait or leave |
| Empty | no file/record/trace returned | Show no data, not zero health |
| Partial | inventory exists but records/trace absent | Keep each boundary visible |
| Offline/error | logger summary unavailable/malformed | Retry bounded read; clear stale data |
| Blocked | 401/403 | Follow access flow; no export |
| Ready | sanitized source fields returned | Read only; no effect claim |

## 5. Purpose-built desktop and web composition

- Desktop/Web: inventory is the primary inspection panel; trace correlation and structured records are separate review surfaces.
- Tablet/mobile stack inventory → trace boundary → records.
- No throughput, error-rate or waterfall chart is rendered without a time-series/trace callable.
- Export remains visibly unavailable until actor-scoped Permission and effect Evidence exist.

## 6. Purpose-built mobile composition

- One active task: determine what operational evidence is actually viewable.
- Keep inventory values and trace-unavailable state above optional records.
- Back/refresh is read-only; no cleanup or export action is exposed.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read summary | SYSTEM Observability GET; per-user scope is a backend gap | Sanitized projection only |
| Export/clear logs | Observability + Permission/effect fence | No control; unavailable |

## 8. Accessibility, motion and localization

- Inventory values and unavailable states have semantic labels; structured records, when present, are text-first.
- Absolute paths, credentials and session material are absent from the accessibility tree.
- No chart alternative is needed while trace/time series is unavailable.
- zh-CN/en/ko copy wraps; reduced motion avoids animated monitoring effects.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS08-SAFE-01 | Path-like names and sensitive log values are not rendered | Snapshot/widget adversarial tests |
| SYS08-TRUTH-01 | Missing metrics do not become zero; no trace does not become a chart | Snapshot/widget tests |
| SYS08-BOUNDARY-01 | Export/clear controls are absent without Permission/effect contracts | Source/widget review |
| SYS08-REAL-USER-01 | Operator reads a real sanitized log summary and sees trace unavailable honestly | Authenticated runtime E2E plus actor-scope decision required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; logs do not establish Global Commercial, Brand or Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no business entity sample, count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified chart/export upgrade until trace, actor authorization, audit and rollback are canonical.
- Decision: `DESIGN_EXPLORATION`; Sol review and live observability acceptance remain pending.
