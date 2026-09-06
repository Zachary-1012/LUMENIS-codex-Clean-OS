# Zachary AI 四库体系 · 跨仓统一系统矩阵
# （原 THREE_REPOSITORY_SYSTEM_MATRIX · 升级 E-001：三仓 → 四库 + AI-DRH）

> Status: ACTIVE DELIVERY CONTROL
> Effective date: 2026-09-02 (last upgrade: E-001)
> Owner: Development-Command-Console (engineering coordination)
> Scope: Z-Brand-Core / SICI-Core / Development-Command-Console / AI-Development-Research-Hub
> 三向验证（业务+工程+移动）域：Z-Brand-Core / DCC / SICI-Core
> 全局基线 & 研究 & 能力注册 Owner：AI-Development-Research-Hub（第四仓）
>
> This document is a coordination matrix. It does not transfer ownership of domain, mobile UI, or production runtime behavior to DCC.

## 1. Authority model

| Area | Authoritative repository | Required evidence |
|---|---|---|
| Domain / business intelligence / production data correctness | Z-Brand-Core | source + database + runtime + applicable tests |
| CTH-POMS production behavior | Z-Brand-Core | fixed SHA + startup/API/E2E + business regression |
| ZBMP capability layer | Z-Brand-Core | source + feature/license gate + compatibility evidence |
| Mobile UI / interaction / device workflow | SICI-Core | source + browser/mobile evidence; real E2E only when controlled backend exists |
| Engineering task / risk / permission / execution policy | DCC | Task Contract + policy/evidence |
| Verification runtime / failure localization / release gate | DCC | fixed SHA + runtime + test output + evidence |
| Cross-repository coordination | DCC | this matrix + explicit contract + verification record |

No repository may silently become owner of another repository's internal logic.

## 2. Contract matrix

| Contract | Owner | Z-Brand-Core | SICI-Core | DCC |
|---|---|---|---|---|
| Task | DCC | consumes | presents/feedback | owns |
| Risk | DCC for engineering risk; Z-Brand for domain risk | owns domain interpretation | consumes/presents | owns engineering gate |
| Permission | DCC | provides required production scope | requests/presents | owns policy gate |
| Execution | DCC | provides target/runtime constraints | initiates approved workflow | owns controlled execution model |
| Evidence | DCC | supplies production evidence | supplies UX/device evidence | owns evidence contract |
| Test | destination repo for native tests; DCC for cross-repo orchestration | owns business tests | owns UI tests | owns orchestration/gates |
| Rollback | destination repository + DCC gate | production rollback | UI/release rollback | policy/evidence gate |
| Session | platform-specific owner | production platform/session state | UI/auth session state | records controlled execution session, never production credentials by default |
| Delivery | destination repo; DCC gates acceptance | owns production release | owns mobile surface release | owns engineering acceptance gate |
| Learning | split by domain/engineering ownership | domain/product learning | UX/workflow learning | engineering learning + promotion gate |

## 3. Runtime matrix

| Runtime | Owner | Status | Allowed responsibility | Must not do |
|---|---|---|---|---|
| Z-Brand production runtime | Z-Brand-Core | production | CTH-POMS / ZBMP controlled business execution | depend on DCC or SICI at runtime |
| Z-Brand collection runtime | Z-Brand-Core | production + controlled adapters | collection, normalization, subject/risk/event/report pipeline | bypass subject/time/data rules |
| SICI browser runtime | SICI-Core | implemented | mobile UI, JS, Python WASM, HTML preview, GitHub read/API surface | pretend browser simulation is server/runtime E2E |
| DCC verification runtime | DCC | implemented | reproducible Python/Node/SQLite/reporting checks | receive production credentials by default; deploy production |
| DCC real execution runtime | DCC | controlled/planned by capability | future sandboxed execution | unrestricted machine privileges |
| Real SICI browser E2E backend | DCC/runtime integration | planned | actual browser automation | be represented by current SICI simulator |

The current SICI E2E simulator remains simulation. A real browser E2E claim requires a controlled backend executor and runtime evidence.

## 4. Evidence matrix

Every material change should be traceable through:

`requirement → owner → baseline SHA → impact → change → runtime → test → result → evidence → risk/permission → acceptance → rollback → release → learning`

Minimum evidence fields:

- repository
- branch
- fixed commit SHA
- change/task identifier
- owner
- runtime/container identity when applicable
- dependency installation result when applicable
- test command/version
- start/end timestamp
- pass/fail/unavailable
- failure classification
- evidence location
- permission/risk state
- acceptance/release state
- rollback reference where applicable
- learning outcome or N/A

### Evidence state rules

- `PLANNED` is not `IMPLEMENTED`.
- `IMPLEMENTED` is not `TESTED`.
- `TESTED` is not `VERIFIED`.
- `VERIFIED` is not `ACCEPTED`.
- `ACCEPTED` is not `RELEASED`.
- AI confidence never upgrades evidence state.
- Repository inspection never upgrades runtime verification state.

## 5. Version truth matrix

Version truth must come from the repository's explicit version source when one exists, then be cross-checked against the fixed SHA and release evidence.

| Repository | Current version source observed | Current declared value | Current rule |
|---|---|---|---|
| Z-Brand-Core | `VERSION` | `5.9.9` | `VERSION` is authoritative version value; README/baselines must not contradict it |
| SICI-Core | no dedicated `VERSION` file found | README: `v3.0` | treat `v3.0` as declared product/UI version until a dedicated version source is introduced |
| DCC | no dedicated `VERSION` file found | README architecture lists V0.4.0 foundation | treat release/commit evidence as authoritative until a dedicated version source is introduced |

Important: commit titles such as automatic-save/inspection labels are not release-version authority.

## 6. Dependency matrix

```text
DCC  ──coordination / verification──> Z-Brand-Core
DCC  ──coordination / verification──> SICI-Core
SICI ──stable contracts/adapters────> DCC
Z-Brand ──stable contracts/evidence─> DCC
```

Forbidden runtime dependency:

```text
CTH-POMS/Z-Brand production → DCC runtime  ✗
CTH-POMS/Z-Brand production → SICI runtime ✗
SICI browser → privileged Z-Brand internals ✗
DCC → duplicated Z-Brand business logic ✗
DCC → duplicated SICI UI logic ✗
```

Integration rule: prefer stable contracts and adapters; never import another repository's private implementation merely to avoid designing a contract.

## 7. Current P0/P1 work order

### P0-A — Freeze facts before changes

1. Resolve version truth from `VERSION`/release evidence.
2. Record current fixed SHA for all three repositories.
3. Record working-tree/inspection evidence where available.
4. Do not treat automatic-save commits as product releases.

### P0-B — Z-Brand / CTH-POMS

1. Startup and dependency reproducibility.
2. Collection health/Auth Recovery/circuit behavior.
3. Subject/time/risk/event/report regression.
4. Database backup/recovery and sensitive-data checks.
5. Public boundary (HTTPS/reverse proxy/tunnel) validation.
6. Key API/page/E2E acceptance.

The following are immutable during this work: `SUBJECT_WORDS`, `SUBJECT_EXCLUDE_WORDS`, `subject_hit()`, `_subject_sql_and_values()`, `aggregate_events()` subject filtering, `build_daily_report()` subject filtering, `publish_datetime`, `captured_at`, historical production data, and core risk/event/report semantics.

### P1-A — ZBMP

1. Continue inside Z-Brand-Core; no second Core.
2. Keep Feature Gate/license boundaries.
3. Keep new adapters Shadow until regression evidence exists.
4. Keep AI optional and non-authoritative.

### P1-B — DCC

1. Turn this matrix into a pre-change checklist.
2. Keep READ/TASK/AUDIT allowed; TEST controlled; WRITE/MERGE/DEPLOY denied by default.
3. Expand cross-repository verification only with least privilege and fixed-SHA evidence.
4. Keep five-times-daily inspection read-only.

### P1/P2-C — SICI

1. Keep mobile-first surface stable.
2. Align UI capability labels with actual browser capabilities.
3. Keep current browser E2E explicitly labelled simulation.
4. Do not escalate browser GitHub credentials into machine/runtime privileges.
5. Introduce a stronger controlled runtime only through DCC permission + verification contracts.

## 8. Change isolation rule

Before modifying any repository:

```text
1. Read all three current baselines.
2. Fix the three-repository SHA snapshot.
3. Identify owner + dependencies + reuse + conflicts.
4. Classify P0/P1/P2.
5. Define the smallest change.
6. Identify cross-repository contracts affected.
7. Verify the destination repository first.
8. Verify compatibility with the other two.
9. Record evidence.
10. Only then promote/release.
```

A change is rejected or paused if it causes:

- duplicated business logic;
- duplicated state ownership;
- hidden runtime dependency;
- credential exposure;
- weakened production boundary;
- unverified production behavior;
- a simulated test to be reported as real E2E;
- a lower-priority capability to block CTH-POMS P0.

## 9. Current audit findings to track

| ID | Finding | Priority | Owner | Action |
|---|---|---|---|---|
| TR-001 | Z-Brand version source says `5.9.9` while some current narrative/automatic-save labels show older versions | P0 governance | Z-Brand + DCC | use `VERSION` + fixed SHA/release evidence; align narrative metadata |
| TR-002 | SICI has no dedicated version source | P1 | SICI | introduce only if useful; otherwise keep declared UI version explicit |
| TR-003 | DCC has no dedicated version source | P1 | DCC | introduce when release/version governance needs it |
| TR-004 | SICI browser runtime exposes only browser/WASM execution; Shell/server runtime is unavailable | P1 | SICI | align capability labels; real backend remains controlled future work |
| TR-005 | SICI GitHub PAT is browser-side/localStorage based | P1/P2 security architecture | SICI + DCC | do not expand privilege; future controlled auth/runtime path |
| TR-006 | Z-Brand mainline contains environment-bound research/inspection artifacts in recent history | P1 hygiene | Z-Brand + DCC | prevent recurrence via ignore/automation policy; archive rather than blindly delete |
| TR-007 | Cross-repository automated verification remains planned | P1 | DCC | implement only with least-privilege private-repo access and real evidence |
| TR-008 | Real browser E2E backend for SICI remains planned | P1/P2 | DCC + SICI | build controlled executor before claiming real browser E2E |

## 10. Non-negotiable operating principle

> **Do not optimize a repository in isolation.**
>
> Every material change must be evaluated against the three-repository matrix first. Preserve existing capabilities, reuse proven contracts, add only the smallest compatible delta, and re-verify at the destination. Evidence observed on one repository is never assumed valid for another without an explicit compatibility check.

Permanent principle:

**三方反哺、互相验证、边界不破、能力共享、责任分明。**
