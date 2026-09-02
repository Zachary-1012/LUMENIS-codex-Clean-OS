# ZBC AI 10× Repo Cleanup & Execution V3

Status: Frozen execution rule
Purpose: achieve materially faster end-to-end delivery by reducing context waste, duplicate implementation, dead files, unnecessary handoffs and rework — without lowering quality, security or compliance standards.

## 1. Non-negotiable outcome

10× means shorter lead time from task intake to verified production-ready commit. It does NOT mean 10× more generated code, skipping tests, or accepting defects.

Quality gates remain unchanged or stronger.

## 2. Clean repository now

The active repository must contain only files that have a verified purpose. Do not keep obsolete files merely “for safety”. Git history is the rollback record.

Before deletion, verify:
- no code import/reference;
- no runtime/build/deployment dependency;
- no test/fixture dependency;
- no workflow/CI dependency;
- no configuration dependency;
- no Evidence/compliance requirement;
- no required documentation link;
- no submodule/generated-artifact contract.

If all checks pass: DELETE, do not archive into old/legacy/backup folders.

Never delete by filename pattern alone.

## 3. Project map first

Maintain a compact machine-readable project map describing active entrypoints, modules, contracts, data flow, test commands, generated files and ownership boundaries. Agents must consult the map before broad exploration.

## 4. Search before create

For every implementation task:
1. locate existing implementation;
2. locate Contract/API/schema;
3. locate tests;
4. locate caller/dependency graph;
5. reuse or extend when appropriate;
6. create a new file only when an existing implementation cannot safely satisfy the requirement.

Do not create duplicate services, utilities, components, schemas or configuration merely because discovery was inconvenient.

## 5. Context minimization

AI agents must load only task-relevant files and dependencies. Prefer symbol/path-specific retrieval over whole-repository reading. Reuse Project Map, Contracts and existing test results.

## 6. Parallel execution

Parallelize independent workstreams when they touch disjoint files/modules. Serialize conflicting edits. Never parallelize changes that can create merge races in the same contract, schema, core service or shared UI component.

Recommended lanes:
- architecture/dependency audit;
- implementation;
- test/security;
- UI/E2E;
- cleanup/evidence.

## 7. Small verified commits

Use small coherent commits. After each material change:
- run targeted tests;
- inspect diff;
- run relevant static/security checks;
- verify UI/API/data path where applicable;
- record Evidence;
- commit.

Do not accumulate dozens of unrelated changes before validation.

## 8. Zero-placeholder rule

No fake success, TODO-only implementation, dead button, swallowed exception, mock path presented as production, empty API response presented as valid data, or hidden failure.

If a capability is not implemented, expose an explicit state and block release rather than pretending completion.

## 9. UI preservation rule

No implementation may remove or silently regress approved visual architecture, interaction states, responsive behavior, loading/empty/error/retry states, accessibility-critical behavior or Light/Dark presentation.

UI completion means UI → API → Service → Data/AI → Result → Evidence is actually connected where the feature requires it.

## 10. Regression shield

Before merge/release, compare against the current production baseline. Existing behavior must remain intact unless the task explicitly changes it and tests prove the intended behavior.

Mandatory scenarios include happy path plus failure paths: network failure, provider failure, expired session, rate limit, security restriction, malformed input, upload failure and permission denial where applicable.

## 11. AI and compliance cannot be weakened for speed

No 10× optimization may:
- bypass platform security or access controls;
- rotate accounts/IPs to evade limits;
- bypass CAPTCHA;
- leak credentials/tokens/cookies;
- bypass ZBC Contracts;
- allow Zachary to redefine business Truth or Policy;
- remove Evidence;
- remove required security/compliance checks.

## 12. Deletion protocol

Deletion is preferred over permanent clutter when a file is proven dead. Preserve history through Git commits/tags/releases where needed, not by keeping dead files in the runtime tree.

If uncertainty remains, STOP deletion and perform dependency tracing. Do not guess.

## 13. Definition of Done

A task is DONE only when:
- implementation complete;
- no duplicate/dead artifacts introduced;
- targeted tests pass;
- relevant regression tests pass;
- security/compliance checks pass or have documented REVIEW disposition;
- UI/E2E passes where applicable;
- Evidence exists;
- diff is clean and scoped;
- commit is pushed.

## 14. Speed metrics

Track:
- task lead time;
- time spent discovering context;
- files changed per task;
- duplicate implementation rate;
- test/rework rate;
- failed CI rate;
- rollback rate;
- dead-file count;
- merge conflict rate;
- verified production-ready commits/week.

The objective is to reduce lead time and rework, not inflate code volume.

## 15. Execution command

For every new task, execute:

AUDIT → MAP → REUSE → IMPLEMENT → TARGET TEST → SECURITY/COMPLIANCE → REGRESSION → CLEAN → EVIDENCE → COMMIT → PUSH.

If a faster path violates any gate, the faster path is invalid.

## 16. Final principle

Keep the product architecture. Remove waste around it. Make the active codebase smaller, clearer and easier for both humans and AI to understand. Let Git history provide rollback instead of preserving dead production files. Move fast, but never move blindly.
