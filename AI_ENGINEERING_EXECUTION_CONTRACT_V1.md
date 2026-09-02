# ZBC AI Engineering Execution Contract V1.0

## Mission
Maximize delivery efficiency without sacrificing correctness, security, compliance, architecture integrity, UI completeness, or existing functionality.

## Non-negotiable quality gates
1. NEVER trade correctness for speed.
2. NEVER remove or silently weaken an existing feature to make a task pass.
3. NEVER rewrite architecture without an evidence-backed need and explicit approval.
4. NEVER introduce placeholder implementations, fake success states, swallowed exceptions, dead buttons, or disconnected UI.
5. NEVER merge code that has not been tested at the affected layer and regression-tested against existing behavior.
6. NEVER expose secrets, cookies, sessions, tokens, personal data, internal paths or credentials in code, logs, screenshots, Evidence or Git.
7. NEVER bypass platform authentication, CAPTCHA, access controls, rate limits or safety restrictions.
8. NEVER allow AI output to silently become business Truth, policy, permission or security configuration.
9. NEVER allow Zachary to cross ZBC product/data/policy boundaries.
10. NEVER claim completion without Evidence.

## 10x efficiency rule
"10x efficiency" means reducing wasted cycles, not reducing validation. Every task should:
- inspect existing implementation before coding;
- reuse stable components/contracts rather than duplicate them;
- batch related analysis and tests where safe;
- identify the smallest safe change set;
- run targeted tests first, then required regression tests;
- report blockers immediately rather than masking them;
- keep commits small, traceable and reversible;
- use automation for repetitive checks;
- avoid re-investigating frozen decisions unless evidence or requirements changed.

## Clean-code gate
Before commit:
- no debug prints or temporary hacks;
- no unused imports/dead code introduced by the change;
- no duplicate implementations where an existing canonical service should be reused;
- no silent exception swallowing;
- no hard-coded secrets or environment-specific credentials;
- no unnecessary dependency additions;
- type/schema/contract consistency verified;
- migrations and rollback implications checked.

## UI visual-completeness gate
Every UI change must preserve the full visual architecture and interaction states:
- light/dark themes where supported;
- responsive desktop/mobile layouts;
- typography hierarchy;
- spacing/grid/radius system;
- semantic status colors;
- hover/active/focus/disabled states;
- loading/empty/error/retry/success states;
- skeleton/progress states where appropriate;
- keyboard/accessibility behavior where applicable;
- no clipped, overlapping, invisible or unreachable controls;
- every visible action must have a functioning backend path or be explicitly marked unavailable;
- screenshots/E2E evidence for material UI changes.

## Functional integrity gate
For every feature:
UI -> API -> Service -> Data -> AI/Tool -> Result -> Evidence
must be traceable. A button that renders but does nothing is a defect. A successful API response with incomplete downstream persistence is a defect. A report that displays data not traceable to stored Evidence is a defect.

## AI engineering gate
AI may generate or modify code, but implementation must be reviewed as software. Record material AI-assisted changes in provenance metadata. AI must not invent requirements, change frozen contracts, or decide that an unverified result is correct.

## Collector safety gate
Collectors must classify platform states and stop/cooldown/human-review when required. Do not implement account switching, proxy rotation, CAPTCHA bypass or access-control circumvention for the purpose of evading platform restrictions.

## Verification protocol
For every completed task:
1. Static/source inspection.
2. Targeted unit/integration tests.
3. E2E test where UI or workflow is affected.
4. Failure-path test.
5. Regression test for adjacent existing functionality.
6. Security check.
7. Compliance check when data/AI/collector behavior is affected.
8. Evidence captured.
9. Commit created with precise message.
10. Push only after all mandatory gates pass.

## Definition of Done
A task is DONE only when code is implemented, tests PASS, UI/functional paths are complete, security/compliance gates pass or have documented REVIEW disposition, Evidence exists, and the commit is pushed. "It runs on my machine" is not completion.

## Priority
P0 blockers > production stability > data integrity > security/compliance > core functionality > UI completeness > optimization > non-critical enhancement.

## Final instruction
Move fast, but never move blindly. Optimize the development process by eliminating repetition and rework while making verification stricter, not weaker. Preserve the existing ZBC architecture and product intent. If a conflict exists between speed and correctness, correctness wins.
