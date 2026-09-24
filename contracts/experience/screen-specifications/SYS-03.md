# SYS-03 — Database and truth chain

```yaml
screen_id: SYS-03
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM / Canonical Data
binding_ids:
  - BACKEND-GAP-038
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYS-03 database/truth-chain blueprint and §36 gates.
- Product contract: `Source → Evidence → Canonical Data → Metric/ViewModel`; version presence is not readability or completeness.
- Historical visual references: `KEEP_AS_EXPLORATION`; the implementation is purpose-built and source-led.
- Anti-template check: the page uses a validation spine, staged chain and check list, not a dashboard grid.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: SYSTEM reader with permitted access to a read-only system screen.
- Real task: understand which schema/check/chain facts are returned and which facts remain unknown.
- Completion signal: schema version, integrity checks, application readability and chain stages remain separate.
- Out of scope: migration, repair, database path disclosure, data rewrite and business metric editing.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-03` → `experience_screens._build_sys03()` → `canonical_data.self_check()` and `get_schema_versions()`.
- Exit: return to the originating SYSTEM route. No migration or recovery destination is bound.
- Return: shell origin, selected context and scroll state only; no business selection changes.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Schema versions | KPI `sys03.schema_versions` | Numeric value only with `ready`; no zero fallback | BACKEND-GAP-038; `experience_screens.py::_build_sys03` |
| P0 | Integrity checks | table rows `检查项/结果/state` | Empty/malformed rows remain unknown/not returned | Canonical self-check owner |
| P0 | Truth stages | optional `truth.truth_chain` or timeline section | Absent stages show that the endpoint did not return them | `sys03_snapshot.dart` |
| P1 | Readability | `truth.application_readability` / `readability_state` | Absent is `notreturned`, not healthy | BACKEND-GAP-038 |
| P1 | DB identity/isolation | `truth.db_identity` state only | No path/connection detail is echoed | Security boundary |

No migration, write, repair, pagination or Evidence emission contract is verified.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | Checks pending | Wait or leave |
| Empty / not collected | No checks or chain stages returned | Show binding-unavailable copy |
| Partial | Schema exists but readability/chain is absent, or checks are mixed | Refresh; do not promote version to healthy |
| Offline / error | Read failed or envelope invalid | Retry bounded GET; clear old snapshot |
| Blocked | 401/403 | Follow shell access flow; no migration control |
| Ready | Specific returned checks are displayed | Read-only; no persisted success claim |

## 5. Purpose-built desktop and web composition

- Desktop: a validation spine anchors schema, integrity and readability; a separate horizontal truth-chain panel shows only returned stages; checks and identity boundary sit beside it.
- Web Workspace shares the same ViewModel and state semantics; no desktop-only database capability is claimed.
- Tablet stacks spine, chain and checks; mobile turns each stage into a readable vertical step.
- No schema/health chart is rendered because no time series is bound.

## 6. Purpose-built mobile composition

- Keep the validation spine visible first, then chain, then checks.
- Each unavailable stage retains its label and unknown state.
- Back/return goes to the originating SYSTEM location; refresh re-reads and clears stale values.

## 7. Actions, authorization and effects

| Action | Boundary | Failure behavior |
| --- | --- | --- |
| Read checks | Existing GET; SYSTEM reader authorization remains a backend gap | Distinguish access denial, offline and malformed data |
| Migration/repair | Not bound | No control is rendered; do not fake authorization or completion |

## 8. Accessibility, motion and localization

- Screen-reader order follows the validation spine and truth-chain stages.
- Stage state is textual and not color-only; unknown/not returned is announced.
- No chart alternative is needed.
- zh-CN/en/ko labels wrap and preserve long check descriptions; reduced motion is supported by the host preference.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS03-TRUTH-01 | Schema version does not imply application readability | Snapshot/widget tests |
| SYS03-CHAIN-01 | Missing chain stages remain unknown/not returned | Snapshot/widget tests |
| SYS03-SAFE-01 | Database path and connection details are never displayed | Adversarial widget test + source review |
| SYS03-REAL-USER-01 | Operator reads a real self-check result and can identify an absent stage without treating it as pass | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; schema/integrity state is infrastructure evidence and does not count Global Commercial, Brand or Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no entity rows are displayed, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade beyond the canonical self-check binding. Recovery/migration requires a separate versioned contract and Permission/Evidence gate.
- Decision: `DESIGN_EXPLORATION`; Sol review and runtime verification remain pending.
