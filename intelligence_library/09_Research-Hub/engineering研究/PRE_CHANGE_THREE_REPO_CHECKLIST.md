# 四库体系 · 变更前检查清单（三向验证+全局基线）
# （原 PRE_CHANGE_THREE_REPO_CHECKLIST · 升级 E-008：三仓 → 四库 + AI-DRH）

> Owner: Development-Command-Console
> Purpose: make the four-repository system matrix executable as a repeatable pre-change gate.
> 三向验证（ZBC 业务 / DCC 工程 / SICI 移动）+ 全局基线（AI-DRH）

## Gate 0 — Freeze facts

- [ ] Record current `main` SHA for Z-Brand-Core.
- [ ] Record current `main` SHA for SICI-Core.
- [ ] Record current `main` SHA for DCC.
- [ ] Record current `main` SHA for AI-Development-Research-Hub（全局基线 & 能力注册表）.
- [ ] Identify explicit version source, if any.
- [ ] Do not use commit-title/version text as a substitute for release evidence.

## Gate 1 — Ownership

- [ ] Is the target capability owned by the destination repository?
- [ ] If shared, is there exactly one owner and a stable contract?
- [ ] Does the change avoid copying another repository's private implementation?

## Gate 2 — Dependency

- [ ] List direct and indirect repository dependencies.
- [ ] Confirm no new production runtime dependency on DCC.
- [ ] Confirm no new production runtime dependency on SICI.
- [ ] Confirm SICI does not gain privileged access to Z-Brand internals.
- [ ] Confirm DCC does not absorb business or UI logic.

## Gate 3 — Contract

- [ ] Task contract identified.
- [ ] Risk owner identified: domain risk vs engineering risk.
- [ ] Permission scope identified.
- [ ] Execution runtime identified.
- [ ] Evidence fields identified.
- [ ] Native test owner identified.
- [ ] Cross-repository compatibility test identified.
- [ ] Rollback owner/path identified.
- [ ] Delivery/release owner identified.
- [ ] Learning outcome identified or marked N/A.

## Gate 4 — Runtime truth

- [ ] Is this repository inspection, simulation, controlled runtime, or production runtime?
- [ ] Is the claimed capability actually executable in that runtime?
- [ ] Are unavailable checks explicitly marked unavailable?
- [ ] Is simulated E2E clearly distinguished from real browser E2E?

## Gate 5 — Evidence

- [ ] Fixed SHA captured.
- [ ] Runtime/container captured where applicable.
- [ ] Dependency result captured where applicable.
- [ ] Test command/version captured.
- [ ] Timestamp captured.
- [ ] Result captured as pass/fail/unavailable.
- [ ] Failure localized before AI intervention.
- [ ] Evidence location recorded.
- [ ] Risk/permission state recorded.

## Gate 6 — Z-Brand production protection

For changes touching Z-Brand-Core/CTH-POMS:

- [ ] `SUBJECT_WORDS` preserved.
- [ ] `SUBJECT_EXCLUDE_WORDS` preserved.
- [ ] `subject_hit()` preserved.
- [ ] `_subject_sql_and_values()` preserved.
- [ ] `aggregate_events()` subject filtering preserved.
- [ ] `build_daily_report()` subject filtering preserved.
- [ ] `publish_datetime` semantics preserved.
- [ ] `captured_at` semantics preserved.
- [ ] Historical production data is not deleted/overwritten.
- [ ] Risk/event/report core semantics remain compatible.
- [ ] Collection/auth/risk failures cannot masquerade as zero data.

## Gate 7 — SICI protection

- [ ] Existing mobile workflow remains usable.
- [ ] UI labels match actual browser capability.
- [ ] Browser E2E simulator remains labelled simulation.
- [ ] No new machine-level privilege is exposed to the browser.
- [ ] GitHub credential handling does not expand privilege without an explicit security review.

## Gate 8 — DCC protection

- [ ] READ/TASK/AUDIT remain allowed.
- [ ] TEST remains controlled.
- [ ] WRITE/MERGE/DEPLOY remain denied by default.
- [ ] Five-times-daily inspection remains read-only.
- [ ] DCC remains outside production runtime.

## Gate 9 — Promotion

A material change may progress only as:

`D0 Idea → D1 Planned → D2 Implemented → D3 Tested → D4 Verified → D5 Accepted → D6 Released → D7 Learned`

Never promote based solely on AI confidence, a code diff, repository inspection, or a simulated test.

## Gate 10 — Post-change learning

- [ ] What failure/success pattern was observed?
- [ ] Can it become a deterministic test/rule/skill?
- [ ] Did complexity increase or decrease?
- [ ] Did duplicated state or coupling increase?
- [ ] Did AI dependence decrease, remain stable, or increase?
- [ ] Was the learning evidence-backed?
