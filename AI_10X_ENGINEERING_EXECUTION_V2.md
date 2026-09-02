# ZBC AI 10× Engineering Execution V2

Status: Engineering execution baseline
Scope: Z-Brand-Core and its coordinated Zachary development workflow

## Objective
Achieve a practical order-of-magnitude improvement in end-to-end delivery throughput by removing context waste, duplicated work, unnecessary files, repeated manual verification and avoidable agent idle time. 10× is a throughput target, not permission to lower quality, safety, compliance or release standards.

## 1. Core rule: optimize the whole pipeline

Optimize:

DISCOVER → PLAN → IMPLEMENT → TEST → REVIEW → CLEAN → EVIDENCE → COMMIT → VERIFY

Do not optimize only code generation. The current research evidence shows AI can substantially increase coding activity while gains attenuate at project/release level; therefore bottlenecks outside code writing must be removed as well. Use repository maps, targeted context, automation and continuous verification rather than larger prompts or longer chats.

## 2. Repository must become lean

Perform an evidence-based repository cleanup NOW. Do not keep obsolete files merely as a temporary backup/archive inside the active source tree.

A file may be deleted when all of the following are true:
- no runtime/build/test/import/reference dependency remains;
- it is not required by deployment, packaging, CI/CD or documentation generation;
- it is not a migration/fixture/schema required for supported versions;
- it is not a security/compliance/Evidence record that must be retained;
- its removal is covered by tests or static/reference verification.

Delete confirmed dead code, duplicate modules, obsolete scripts, abandoned UI assets, generated junk, stale temporary files, redundant docs and unused configuration. Do not preserve dead files solely because they are old.

Before deletion, produce a machine-readable cleanup manifest containing path, reason, reference check and verification result. Never delete live production data, secrets, credentials, Evidence or required compliance records as part of code cleanup.

## 3. No 'old version parking' in active code

Do NOT create folders such as old/, backup/, legacy/, v1-old/, temp-backup/ merely to avoid making a decision. Git history is the rollback mechanism for source code. Required historical records belong in Git history, tagged releases or the appropriate Evidence/compliance store—not duplicated inside runtime source directories.

## 4. Repository map first

Maintain a compact canonical project map describing:
- entrypoints;
- runtime services;
- frontend modules;
- collectors;
- database/schema;
- AI/runtime providers;
- tests;
- build/deploy;
- contracts/policies;
- compliance/evidence;
- generated artifacts.

Agents must read the map and the relevant path-specific instructions before scanning the whole repository.

## 5. Context economy

Never load the entire repository into an AI context when a targeted slice is sufficient. Use repository-wide instructions plus path-specific instructions. Keep sessions/task contexts focused; compact or restart when context becomes stale or unrelated. Enable only the tools required for the task.

This follows current agent-development guidance: repository instructions reduce orientation cost, path-specific rules prevent irrelevant context, and lean context reduces token/time overhead. GitHub documents repository-wide, path-specific and agent instructions for exactly this purpose. 

## 6. Task decomposition

Every work order must be split into independent, testable units with explicit acceptance criteria. Prefer parallel work only when tasks have no overlapping write surface or dependency. Never parallelize two agents that can modify the same file/contract without coordination.

Recommended lanes:
- Lane A: architecture/dependency audit;
- Lane B: implementation;
- Lane C: tests/security;
- Lane D: UI/E2E;
- Lane E: cleanup/provenance/evidence.

Merge only after contract and tests pass.

## 7. Reuse before invention

Before adding a new file, service, component, helper or dependency:
1. search for an existing implementation;
2. check the canonical contract;
3. reuse if compatible;
4. refactor only if the existing implementation is genuinely unsuitable;
5. document why a new implementation is necessary.

Duplicate implementations are a P1 defect and should be removed when safely consolidated.

## 8. One change, one verification loop

For each change:
- identify affected paths;
- make the smallest coherent change;
- run the narrowest relevant test immediately;
- run broader regression tests after the unit is green;
- inspect the diff;
- record Evidence;
- commit a coherent unit.

Do not accumulate dozens of unverified changes before testing.

## 9. Definition of DONE

A task is not done merely because code exists. DONE requires:
- implementation complete;
- no known functional regression;
- relevant tests pass;
- UI path works where applicable;
- security checks pass where applicable;
- compliance gate passes where applicable;
- cleanup completed;
- Evidence recorded;
- diff reviewed;
- commit/push completed.

## 10. Zero-error objective without false guarantees

Target zero known functional defects at release. Never claim 'zero bugs' or '100% safe' without test evidence. If a defect is found, stop propagation, reproduce, fix, regression-test and record it.

## 11. UI preservation

No cleanup or refactor may remove or silently alter existing UI visual architecture, states, interaction paths or responsive behavior unless the work order explicitly requires it. Every affected UI feature must verify:
- loading;
- empty;
- success;
- error;
- retry;
- disabled;
- permission/auth state;
- light/dark;
- mobile/web where supported;
- keyboard/accessibility basics where applicable.

## 12. Performance and architecture

Prefer fewer layers, fewer duplicate transformations, fewer network round trips, smaller dependency surfaces and deterministic interfaces. Measure before/after where feasible. Do not introduce microservices or abstractions merely to appear sophisticated.

## 13. AI agent operating mode

AI coding agents must:
- inspect before edit;
- use the canonical project map;
- follow repository/path instructions;
- avoid broad speculative rewrites;
- make bounded changes;
- test automatically;
- repair failures before moving on;
- report exact changed files and evidence;
- stop when a policy/security boundary is reached.

Agents must not invent completion, suppress failing tests, bypass policy, or hide warnings.

## 14. 10× KPI dashboard

Track actual throughput rather than claiming a fixed multiplier:
- lead time from task start to verified commit;
- rework rate;
- failed CI rate;
- test pass rate;
- defect escape rate;
- context/token consumption where available;
- agent idle time;
- duplicate-file count;
- dead-code count;
- dependency count;
- average files touched per task;
- release frequency.

The goal is to drive the bottleneck out of the system continuously.

## 15. Safety and compliance remain immutable

10× speed never authorizes:
- bypassing platform security or access controls;
- CAPTCHA circumvention;
- credential/token/cookie theft;
- security-control weakening;
- deletion of Evidence/compliance records;
- disabling tests to make CI green;
- copying third-party code without provenance/license review;
- changing ZBC Subject Truth or business policy without the approved contract.

## 16. Cleanup execution order

Immediately execute:
1. repository inventory;
2. dependency/reference graph;
3. identify confirmed dead/duplicate/generated artifacts;
4. generate cleanup manifest;
5. delete confirmed dead files from active source tree;
6. run tests/build/type/lint/security checks;
7. inspect UI/E2E;
8. update project map;
9. record Evidence;
10. commit/push;
11. continue to the next P0 work order.

Do not postpone confirmed dead-file deletion to a future 'cleanup phase'.

## 17. Final principle

The desired state is not 'more AI writes more code'. It is a lean repository plus precise contracts plus targeted context plus parallelizable tasks plus immediate verification plus automatic cleanup plus auditable delivery.

Move 10× faster by eliminating waste, not by lowering standards.
